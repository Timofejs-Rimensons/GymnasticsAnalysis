import json
import numpy as np
import torch
from collections import Counter
from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository
from services.ClassifyingService import ClassifyingService
from services.VisualisationService import save_visualized_video
from services.PdfReportService import generate_pdf_report
from services.HandstandAnalyticsService import HandstandAnalyticsService
from services.LeapAnalyticsService import LeapAnalyticsService

class ProcessingPipelineService:
    
    def __init__(self):
        with open("config.json", 'r') as config_file:
            self.config = json.load(config_file)
            
        self.improvement_needed_treshold = self.config.get("improvement_needed_treshold", 0.7)
        self.segmentation_repository = MediapipeSegmentationRepository()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def _update_status(self, status_json_path: str, status: str, progress: float):
        try:
            with open(status_json_path, 'r+') as f:
                status_data = json.load(f)
                status_data['status'] = status
                status_data['progress'] = progress
                f.seek(0)
                json.dump(status_data, f)
                f.truncate()
        except (FileNotFoundError, json.JSONDecodeError):
            with open(status_json_path, 'w') as f:
                json.dump({'status': status, 'progress': progress}, f)

    def _structure_and_save_results(self, all_scores, analytics_per_pose, output_json_path, output_pdf_path):
        pose_scores = {pose: np.mean(scores) for pose, scores in all_scores.items() if scores}
        
        scores = list(pose_scores.values())
        overall_score = np.mean(scores) if scores else 0

        pose_categories = []
        for pose, score in pose_scores.items():
            improvement_needed = bool(score < self.improvement_needed_treshold)
            
            pose_errors = []
            if pose in analytics_per_pose:
                aggregated = analytics_per_pose[pose]
                pose_errors = aggregated.get('common_errors', [])
            
            pose_categories.append({
                "name": pose,
                "score": round(score * 100),
                "max_score": 100,
                "description": f"Analysis of {pose} phase",
                "improvement_needed": improvement_needed,
                "errors": pose_errors
            })
            
        results = {
            "overall_score": round(overall_score * 100),
            "max_score": 100,
            "percentage": overall_score * 100,
            "categories": [{"name": "Poses", "poses": pose_categories}]
        }
        generate_pdf_report(analysis=results, output_path=output_pdf_path)

        with open(output_json_path, 'w') as json_file:
            json.dump(results, json_file, indent=4)

    def _process_labels(self, labels, exercise_name):
        corrected_labels = labels.copy()

        if exercise_name == 'handstand':
            # Handstand specific logic to correct starting/landing confusion
            swing_handstand_indices = [i for i, label in enumerate(labels) if label in ['Swing', 'Handstand']]
            if swing_handstand_indices:
                mean_index = np.mean(swing_handstand_indices)
                # Use first and last poses from config
                pose_names = self.config['models']['handstand']['poses']
                starting_pose = pose_names[0]
                landing_pose = pose_names[-1]
                
                for i, label in enumerate(corrected_labels):
                    if i < mean_index and label == landing_pose:
                        corrected_labels[i] = starting_pose
                    elif i > mean_index and label == starting_pose:
                        corrected_labels[i] = landing_pose
        
        # General logic to group labels together
        label_counts = Counter(corrected_labels)
        label_avg_positions = {label: np.mean([i for i, l in enumerate(corrected_labels) if l == label]) for label in set(corrected_labels)}
        
        sorted_labels_by_pos = sorted(label_avg_positions.keys(), key=lambda x: label_avg_positions[x])
        
        grouped_labels = []
        for label in sorted_labels_by_pos:
            grouped_labels.extend([label] * label_counts[label])
            
        return grouped_labels

    def analyze_video(self, input_video_path: str, output_video_path: str, output_pdf_path: str, output_json_path: str, exercise_name: str, status_json_path: str):
        self._update_status(status_json_path, "processing", 0.1)

        model_config = self.config['models'].get(exercise_name)
        if not model_config:
            raise ValueError(f"Exercise '{exercise_name}' not found in config.")

        # 1. Load services
        classifier = ClassifyingService.load(model_config['model_path'], device=self.device)
        pose_labels = model_config['poses']
        
        analytics_service_class = HandstandAnalyticsService if exercise_name == 'handstand' else LeapAnalyticsService
        analytics_service = analytics_service_class(config=self.config.get('pose_criteria', {}))

        self._update_status(status_json_path, "processing", 0.2)

        # 2. Get features and frames
        frames_data, feature_tensor, mask = self.segmentation_repository.process_video_stgcn(input_video_path)
        _, world_pose_tensor, _ = self.segmentation_repository.process_video(input_video_path)

        if feature_tensor is None or feature_tensor.shape[1] == 0:
            self._update_status(status_json_path, "completed", 1)
            return

        self._update_status(status_json_path, "processing", 0.5)

        # 3. Get frame-by-frame predictions and process them
        raw_labels = classifier.predict_frame_by_frame(feature_tensor, class_names=pose_labels)
        processed_labels = self._process_labels(raw_labels, exercise_name)

        self._update_status(status_json_path, "processing", 0.7)

        # 4. Perform analytics on each frame
        all_scores = {label: [] for label in pose_labels}
        analytics_per_frame = []
        
        for i, pose_name in enumerate(processed_labels):
            analytics_result = None
            if i < len(world_pose_tensor):
                current_world_pose = world_pose_tensor[i]
                analytics_result = analytics_service.analyze_pose(current_world_pose, pose_name)
                if analytics_result and 'score' in analytics_result:
                    all_scores[pose_name].append(analytics_result['score'])
            analytics_per_frame.append(analytics_result)

        # 5. Aggregate analytics
        analytics_per_pose = {}
        for pose_name in pose_labels:
            pose_specific_analytics = [res for i, res in enumerate(analytics_per_frame) if processed_labels[i] == pose_name and res]
            if pose_specific_analytics:
                analytics_per_pose[pose_name] = analytics_service.aggregate_frame_feedback(pose_specific_analytics)

        self._update_status(status_json_path, "saving", 0.9)

        # 6. Save results
        self._structure_and_save_results(all_scores, analytics_per_pose, output_json_path, output_pdf_path)
        
        # 7. Create annotated video
        frame_annotations = [
            {
                "label": (
                    f"{processed_labels[i]} | Score: {analytics_per_frame[i]['score']:.2f}"
                    if analytics_per_frame[i] and 'score' in analytics_per_frame[i]
                    else processed_labels[i]
                ),
                "segment_scores": (
                    analytics_per_frame[i]['bone_scores']
                    if analytics_per_frame[i] and 'bone_scores' in analytics_per_frame[i]
                    else None
                )
            }
            for i in range(len(processed_labels))
        ]
        save_visualized_video(output_video_path, frames_data, input_video_path, frame_annotations=frame_annotations)
        
        self._update_status(status_json_path, "completed", 1)