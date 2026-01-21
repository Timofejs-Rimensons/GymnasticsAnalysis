import json
import os
import numpy as np
import torch
import cv2
from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository
from services.ClassifyingService import ClassifyingService
from services.ScoringService import ScoringService
from services.VisualisationService import save_visualized_video
from services.PdfReportService import generate_pdf_report
from services.PoseAnalyticsService import PoseAnalyticsService

class ProcessingPipelineService:
    
    def __init__(self):
        with open("./config.json", 'r') as config_file:
            self.config = json.load(config_file)
            
        self.improvement_needed_treshold = self.config.get("improvement_needed_treshold", 0)
        self.segmentation_repository = MediapipeSegmentationRepository()
        
        # Initialize analytics service
        self.analytics_service = PoseAnalyticsService(
            config=self.config.get('pose_criteria', {})
        )
        
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.classifier = None
        self.scoring_models = {}
        self._load_models()

    def _load_models(self):
        """Loads the classifier and all scoring models from the config."""
        exercises = self.config.get('models', {})
        for exercise_name, exercise_config in exercises.items():
            # Load classifier for the exercise
            class_names = list(exercise_config['poses'].keys())
            self.classifier = ClassifyingService(
                num_classes=len(class_names),
                class_names=class_names,
                device=self.device,
                model_path=exercise_config['model_rel_path']
            )

            # Load scoring models for each pose and sub-pose
            for pose_name, pose_config in exercise_config['poses'].items():
                if 'model_rel_path' in pose_config and pose_config['model_rel_path']:
                    self._load_scoring_model(pose_config['model_rel_path'])
                
                if 'sub_poses' in pose_config:
                    for sub_pose_name, sub_pose_config in pose_config['sub_poses'].items():
                        if 'model_rel_path' in sub_pose_config and sub_pose_config['model_rel_path']:
                            self._load_scoring_model(sub_pose_config['model_rel_path'])

    def _load_scoring_model(self, model_path):
        """Loads a single scoring model if it's not already loaded."""
        if model_path not in self.scoring_models:
            scorer = ScoringService(device=self.device)
            scorer.load_model(model_path)
            self.scoring_models[model_path] = scorer

    def _update_status(self, status_json_path: str, status: str, progress: float):
        try:
            with open(status_json_path, 'r+') as f:
                try:
                    status_data = json.load(f)
                except json.JSONDecodeError:
                    status_data = {}
                
                status_data['status'] = status
                status_data['progress'] = progress
                
                f.seek(0)
                json.dump(status_data, f)
                f.truncate()
        except FileNotFoundError:
            with open(status_json_path, 'w') as f:
                json.dump({'status': status, 'progress': progress}, f)

    def _structure_and_save_results(self, pose_scores_per_frame, analytics_per_frame, output_json_path, output_pdf_path):
        all_poses = {}
        pose_analytics = {}  # Collect analytics by pose type
        
        for frame_idx, frame_scores in enumerate(pose_scores_per_frame):
            phase_name = frame_scores.get('phase')
            
            # Collect analytics for this pose phase
            if phase_name and phase_name != 'no_pose':
                if analytics_per_frame and frame_idx < len(analytics_per_frame):
                    analytics = analytics_per_frame[frame_idx]
                    if analytics:
                        if phase_name not in pose_analytics:
                            pose_analytics[phase_name] = []
                        pose_analytics[phase_name].append(analytics)
            
            for pose_name, data in frame_scores.items():
                if pose_name == 'phase':
                    continue
                if 'sub_scores' in data and data['sub_scores']:
                    all_poses[pose_name] = []
                    for sub_pose, sub_score in data['sub_scores'].items():
                        if sub_pose not in all_poses:
                            all_poses[sub_pose] = []
                        all_poses[sub_pose].append(sub_score)
                        all_poses[pose_name].append(sub_score)
                else:
                    if pose_name not in all_poses:
                        all_poses[pose_name] = []
                    all_poses[pose_name].append(data.get('score', 0))

        
        pose_scores = {pose: np.mean(scores) for pose, scores in all_poses.items() if scores}
        
        scores = list(pose_scores.values())
        if not scores:
            overall_score_raw = 0
            max_raw_score = 1
        else:
            overall_score_raw = sum(scores)
            max_raw_score = len(pose_scores)

        target_max_score = 100.0
        individual_pose_max_score = target_max_score / max_raw_score if max_raw_score > 0 else 0 if max_raw_score > 0 else 0
        
        overall_score = (overall_score_raw / max_raw_score) * target_max_score if max_raw_score > 0 else 0
        percentage = overall_score 

        pose_categories = []
        for pose, score in pose_scores.items():
            improvement_needed = bool(score < self.improvement_needed_treshold)
            
            # Get aggregated analytics for this pose
            pose_errors = []
            if pose in pose_analytics:
                aggregated = self.analytics_service.aggregate_frame_feedback(pose_analytics[pose])
                pose_errors = aggregated.get('common_errors', [])
            
            pose_categories.append({
                "name": pose,
                "score": round(score * individual_pose_max_score),
                "max_score": round(individual_pose_max_score),
                "description": f"Analysis of {pose} phase",
                "improvement_needed": improvement_needed,
                "errors": pose_errors
            })
            
        results = {
            "overall_score": round(overall_score),
            "max_score": target_max_score,
            "percentage": percentage,
            "categories": [
                {
                    "name": "Poses",
                    "poses": pose_categories
                }
            ]
        }
        generate_pdf_report(analysis=results, output_path=output_pdf_path)

        with open(output_json_path, 'w') as json_file:
            json.dump(results, json_file, indent=4)

    def process_video(self, video_path, exercise_config):
        frames_data, feature_tensor, mask = self.segmentation_repository.process_video_cosine_segments(video_path)
        
        # Also get 3D world pose data for analytics
        _, world_pose_tensor, _ = self.segmentation_repository.process_video(video_path)
        
        if feature_tensor.shape[0] == 0:
            return [], None, None, None, None
        
        skeletons_masked = feature_tensor[mask]
        feature_0 = skeletons_masked[:, :, 0]
        feature_1 = skeletons_masked[:, :, 1]
        skeletons = np.hstack((feature_0, feature_1))

        predictions, _ = self.classifier.predict_frames([skeletons], return_probabilities=True)
        frame_poses = predictions[0]
        
        pose_scores_per_frame = []
        segment_scores_per_frame = []  # Store segment scores separately
        analytics_per_frame = []  # Store analytics results

        class_names = list(exercise_config['poses'].keys())
        num_segments = feature_0.shape[1]  # Number of body segments
        
        original_frame_pose_names = ['no_pose'] * len(mask)
        original_frame_segment_scores = [None] * len(mask)
        original_frame_analytics = [None] * len(mask)  # Track analytics for all frames
        
        mask_indices = np.where(mask)[0]
        for i, predicted_pose_idx in enumerate(frame_poses):
            original_frame_idx = mask_indices[i]
            pose_name = class_names[predicted_pose_idx]
            original_frame_pose_names[original_frame_idx] = pose_name

        for i, pose_name in enumerate(original_frame_pose_names):
            if pose_name == 'no_pose':
                pose_scores_per_frame.append({'phase': 'no_pose'})
                segment_scores_per_frame.append(None)
                analytics_per_frame.append(None)
                continue

            pose_info = exercise_config['poses'][pose_name]
            frame_scores = {'phase': pose_name}
            current_segment_scores = {}  # Collect segment scores for this frame
            
            # Find the index in the masked skeleton array
            skeleton_in_valid_poses_idx = np.where(mask_indices == i)[0]
            
            if skeleton_in_valid_poses_idx.size == 0:
                pose_scores_per_frame.append(frame_scores)
                segment_scores_per_frame.append(None)
                analytics_per_frame.append(None)
                continue
                
            current_skeleton = skeletons[skeleton_in_valid_poses_idx[0]]
            
            # Get 3D world pose for this frame
            current_world_pose = world_pose_tensor[i] if i < len(world_pose_tensor) else None
            
            if 'model_rel_path' in pose_info and pose_info['model_rel_path']:
                scorer = self.scoring_models.get(pose_info['model_rel_path'])
                if scorer:
                    # Get per-segment scores from the model
                    scores_output = scorer.predict_frames([[current_skeleton]])[0][0]
                    
                    # If scores_output is multi-dimensional (per-segment), store them
                    if hasattr(scores_output, '__len__') and len(scores_output) > 1:
                        score = float(np.mean(scores_output))
                        current_segment_scores = {k: float(v) for k, v in enumerate(scores_output)}
                    else:
                        score = float(scores_output[0]) if hasattr(scores_output, '__len__') else float(scores_output)
                        
                    frame_scores[pose_name] = {'score': score, 'sub_scores': {}}
            
            if 'sub_poses' in pose_info:
                if pose_name not in frame_scores:
                    frame_scores[pose_name] = {'score': 0, 'sub_scores': {}}
                    
                sub_pose_segment_scores = {}
                
                for sub_pose_name, sub_pose_info in pose_info['sub_poses'].items():
                    scorer = self.scoring_models.get(sub_pose_info['model_rel_path'])
                    if scorer:
                        segment_mask = sub_pose_info.get('segment_mask')
                        
                        if segment_mask:
                            # Apply segment mask to get sub-pose features
                            mask_indices_for_features = np.array(segment_mask + [s + num_segments for s in segment_mask])
                            sub_pose_features = current_skeleton[mask_indices_for_features]
                        else:
                            sub_pose_features = current_skeleton
                        
                        # Get per-segment scores from the sub-pose model
                        sub_scores_output = scorer.predict_frames([[sub_pose_features]])[0][0]
                        
                        if hasattr(sub_scores_output, '__len__') and len(sub_scores_output) > 1:
                            sub_score = float(np.mean(sub_scores_output))
                            # Map back segment scores to original segment indices
                            if segment_mask:
                                for idx, seg_idx in enumerate(segment_mask):
                                    sub_pose_segment_scores[seg_idx] = float(sub_scores_output[idx])
                            else:
                                sub_pose_segment_scores.update({k: float(v) for k, v in enumerate(sub_scores_output)})
                        else:
                            sub_score = float(sub_scores_output[0]) if hasattr(sub_scores_output, '__len__') else float(sub_scores_output)
                        
                        frame_scores[pose_name]['sub_scores'][sub_pose_name] = sub_score
                
                # Merge sub-pose segment scores into current_segment_scores
                current_segment_scores.update(sub_pose_segment_scores)
                
                # Calculate parent score as mean of sub-pose scores
                if frame_scores[pose_name]['sub_scores']:
                    frame_scores[pose_name]['score'] = np.mean(list(frame_scores[pose_name]['sub_scores'].values()))
            
            # Run analytics on this frame
            analytics_result = None
            if current_world_pose is not None:
                try:
                    analytics_result = self.analytics_service.analyze_pose(
                        current_world_pose,
                        pose_name
                    )
                    print(f"Frame {i}: {pose_name} - Analytics score: {analytics_result.get('score', 0):.2f}, Errors: {len(analytics_result.get('errors', []))}")
                except Exception as e:
                    print(f"Analytics error at frame {i}: {e}")
            else:
                print(f"Frame {i}: No world pose data available for analytics")

            pose_scores_per_frame.append(frame_scores)
            segment_scores_per_frame.append(current_segment_scores if current_segment_scores else None)
            analytics_per_frame.append(analytics_result)
            
        return pose_scores_per_frame, frames_data, segment_scores_per_frame, mask, analytics_per_frame

    def analyze_video(self, input_video_path: str, output_video_path: str, output_pdf_path: str, output_json_path: str, exercise_name: str, status_json_path: str):
        input_video_path = str(input_video_path)
        output_video_path = str(output_video_path)
        output_pdf_path = str(output_pdf_path)
        output_json_path = str(output_json_path)
        status_json_path = str(status_json_path)
        
        exercise_config = self.config['models'].get(exercise_name)
        if not exercise_config:
            raise ValueError(f"Exercise '{exercise_name}' not found in config.")

        # Updated to receive analytics_per_frame
        pose_scores_per_frame, frames_data, segment_scores_per_frame, mask, analytics_per_frame = self.process_video(input_video_path, exercise_config)
        
        if not pose_scores_per_frame:
            with open(output_json_path, 'w') as json_file:
                json.dump({}, json_file)
            generate_pdf_report(analysis={}, output_path=output_pdf_path)
            self._update_status(status_json_path, "completed", 1)
            return

        self._structure_and_save_results(pose_scores_per_frame, analytics_per_frame, output_json_path, output_pdf_path)

        frame_annotations = []
        for idx, frame_scores in enumerate(pose_scores_per_frame):
            top_pose_name = frame_scores.get('phase')
            annotation = {"label": "None", "segment_scores": None}
            
            if top_pose_name and top_pose_name != "no_pose":
                top_pose_data = frame_scores.get(top_pose_name)
                if top_pose_data:
                    score = top_pose_data.get('score', 0)
                    label = f"{top_pose_name} | Score: {score:.2f}"
                    
                    sub_scores = top_pose_data.get('sub_scores')
                    if sub_scores:
                        avg_sub_score = np.mean(list(sub_scores.values())) if sub_scores else 0
                        label = f"{top_pose_name} | Score: {avg_sub_score:.2f}"
                        # Optionally append sub-score details
                        label += " | " + " | ".join([f"{name}: {s:.2f}" for name, s in sub_scores.items()])
                    
                    annotation["label"] = label
                    
                    # NEW: Add segment_scores from the collected data
                    if segment_scores_per_frame and idx < len(segment_scores_per_frame):
                        annotation["segment_scores"] = segment_scores_per_frame[idx]

            frame_annotations.append(annotation)

        save_visualized_video(output_video_path, frames_data, input_video_path, frame_annotations=frame_annotations)
        
        self._update_status(status_json_path, "completed", 1)