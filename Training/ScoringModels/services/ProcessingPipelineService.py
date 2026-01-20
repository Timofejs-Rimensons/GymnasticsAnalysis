import json
import os
import numpy as np
from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository
from services.VisualisationService import save_visualized_video
from services.ClassifyingService import ClassifyingService
from services.ScoringService import ScoringService

class ProcessingPipelineService:
    def __init__(self, config_path="config.json"):
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Assuming one exercise type for now, e.g., 'handstand'
        exercise_key = list(config['models'].keys())[0]
        self.exercise_config = config['models'][exercise_key]
        
        self.poses_config = self.exercise_config['poses']
        self.num_segments = 10 # This should probably be in the config too

        # Create a mapping from pose_idx to pose_name for convenience
        self.idx_to_pose_name = {}
        for name, p_config in self.poses_config.items():
            self.idx_to_pose_name[p_config['pose_idx']] = name
            if 'sub_poses' in p_config and p_config['sub_poses']:
                for sub_name, sub_p_config in p_config['sub_poses'].items():
                    self.idx_to_pose_name[sub_p_config['pose_idx']] = sub_name

        # Initialize services and repositories
        self.segmentation_repo = MediapipeSegmentationRepository()
        
        # --- Load Classifier ---
        classifier_path = self.exercise_config['model_rel_path']
        # These details should match the saved classifier's training
        self.classifier = ClassifyingService(
            num_classes=len(self.poses_config),
            input_size=self.num_segments * 2, # Default input size
            class_names=tuple(self.poses_config.keys())
        )
        self.classifier.load_model(classifier_path)

        # --- Load All Scoring Models ---
        self.scoring_models = {}
        for pose_name, pose_config in self.poses_config.items():
            # Load models for sub-poses
            if 'sub_poses' in pose_config and pose_config['sub_poses']:
                for sub_pose_name, sub_pose_config in pose_config['sub_poses'].items():
                    self._load_scorer(sub_pose_config, sub_pose_id=sub_pose_config['pose_idx'], parent_id=pose_config['pose_idx'])
            # Load model for regular pose
            elif 'model_rel_path' in pose_config:
                self._load_scorer(pose_config, pose_config['pose_idx'])

    def _load_scorer(self, config, pose_id, parent_id=None):
        model_path = config['model_rel_path']
        if os.path.exists(model_path):
            segment_mask = config.get('segment_mask')
            input_size = len(segment_mask) * 2 if segment_mask else self.num_segments * 2
            num_outputs = len(segment_mask) if segment_mask else self.num_segments

            scorer = ScoringService(num_outputs=num_outputs)
            scorer.input_size = input_size
            scorer.load_model(model_path)
            
            self.scoring_models[pose_id] = {
                'model': scorer, 
                'config': config, 
                'parent_id': parent_id
            }

    def process_video(self, video_path):
        # 1. Process video to get features
        _, feature_tensor, mask = self.segmentation_repo.process_video_cosine_segments(video_path)
        
        # Ensure video_features is a NumPy array for easier slicing
        video_features = np.array([[segment[0] for segment in frame] + [segment[1] for segment in frame] for frame in feature_tensor[mask].tolist()])

        # 2. Predict poses for the valid frames
        predictions, _ = self.classifier.predict_frames(
            [video_features], 
            inertia_factor=0.3, # Using new inertia logic
            min_pose_duration=5
        )
        predicted_poses = predictions[0]

        # 3. Process segments, get scores, and prepare annotations
        frame_annotations = [{} for _ in range(len(feature_tensor))] # Annotations for original number of frames
        valid_frame_indices = np.where(mask)[0]

        all_scores_overall = []
        if len(predicted_poses) == 0:
            return {}, 0.0

        current_pose_id = predicted_poses[0]
        segment_start_idx = 0
        
        # Loop through segments of predicted poses
        for i in range(1, len(predicted_poses) + 1):
            if i == len(predicted_poses) or predicted_poses[i] != current_pose_id:
                segment_end_idx = i
                segment_features = video_features[segment_start_idx:segment_end_idx]

                # Find the config for the current pose
                is_parent_pose = False
                parent_pose_config = None
                for name, cfg in self.poses_config.items():
                    if cfg['pose_idx'] == current_pose_id and 'sub_poses' in cfg and cfg['sub_poses']:
                        is_parent_pose = True
                        parent_pose_config = cfg
                        break
                
                # --- Scoring Logic ---
                if is_parent_pose:
                    child_scores = []
                    for sub_pose_name, sub_pose_config in parent_pose_config['sub_poses'].items():
                        sub_pose_id = sub_pose_config['pose_idx']
                        scorer_info = self.scoring_models.get(sub_pose_id)
                        
                        if scorer_info and len(segment_features) > 0:
                            sub_scorer = scorer_info['model']
                            segment_mask = scorer_info['config'].get('segment_mask')
                            
                            if segment_mask:
                                masked_features = np.hstack([
                                    segment_features[:, np.array(segment_mask)],
                                    segment_features[:, self.num_segments + np.array(segment_mask)]
                                ])
                            else:
                                masked_features = segment_features

                            sub_scores_per_frame = sub_scorer.predict_frames([masked_features])[0]
                            child_scores.append(sub_scores_per_frame.mean())
                            all_scores_overall.extend(list(sub_scores_per_frame.flatten()))

                elif current_pose_id in self.scoring_models and len(segment_features) > 0:
                    scorer_info = self.scoring_models[current_pose_id]
                    scorer_model = scorer_info['model']
                    segment_scores_per_frame = scorer_model.predict_frames([segment_features])[0]
                    all_scores_overall.extend(list(segment_scores_per_frame.flatten()))
                    
                    overall_segment_score = segment_scores_per_frame.mean()
                    
                    # Annotate frames for this regular segment
                    for j in range(segment_start_idx, segment_end_idx):
                        original_frame_idx = valid_frame_indices[j]
                        avg_frame_score = segment_scores_per_frame[j - segment_start_idx].mean()
                        frame_annotations[original_frame_idx]['label'] = f'{self.idx_to_pose_name.get(current_pose_id, "Unknown")}: {avg_frame_score:.2f}'

                # Update for next segment
                if i < len(predicted_poses):
                    current_pose_id = predicted_poses[i]
                    segment_start_idx = i

        final_score = np.mean(all_scores_overall) if all_scores_overall else 0.0
        return frame_annotations, final_score