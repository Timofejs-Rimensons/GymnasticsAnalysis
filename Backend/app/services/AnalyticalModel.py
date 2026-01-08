import numpy as np
import json
from pathlib import Path
from tqdm import tqdm
import os

# Assuming the new, fixed repository is now the one to be used.
# Make sure fixed.py is in the repositories folder.
from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository

class AnalyticalModel:
    def __init__(self, reference_json_path):
        self.reference_json_path = reference_json_path
        # Ensure the JSON file exists, creating it if necessary.
        if not os.path.exists(self.reference_json_path):
            with open(self.reference_json_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
        
        self.segmentor = MediapipeSegmentationRepository()
        self.video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]

    def _get_video_files(self, folder):
        folder_path = Path(folder)
        return [
            str(p)
            for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() in self.video_extensions
        ]

    @staticmethod
    def _similarity_score(frame_features, pose_mean, pose_std, segment_mask, feature_mask):
        """
        Calculates a similarity score based on masked segments and features.
        """
        # Ensure inputs are numpy arrays
        frame_features = np.asarray(frame_features)
        pose_mean = np.asarray(pose_mean)
        pose_std = np.asarray(pose_std)
        segment_mask = np.asarray(segment_mask)
        feature_mask = np.asarray(feature_mask)

        # Select the relevant segments (rows) and features (columns) for scoring
        relevant_features = frame_features[segment_mask][:, feature_mask]
        relevant_mean = pose_mean[segment_mask][:, feature_mask]
        relevant_std = pose_std[segment_mask][:, feature_mask]
        
        # Calculate Z-score distance only on the selected elements
        z_distance = (relevant_features - relevant_mean) / (relevant_std + 1e-8)
        mean_abs_z_distance = np.mean(np.abs(z_distance))
        
        return float(np.exp(-mean_abs_z_distance))

    def fit(self, pose_name, pose_videos_folder, pose_config={}):
        """
        Fits a model for a given pose and saves its configuration and statistical data.
        """
        print(f"Fitting model for pose: '{pose_name}'...")
        
        with open(file=self.reference_json_path, mode='r', encoding='utf-8') as file:
            reference_data = json.load(file)

        # For composite poses, just store the config, no stats needed.
        if "sub_poses" in pose_config:
            reference_data[pose_name] = {"config": pose_config}
            print(f"  - Composite pose detected. Aggregates: {pose_config['sub_poses']}")
        # For fundamental poses, calculate stats and store with config.
        else:
            videos = self._get_video_files(pose_videos_folder)
            if not videos:
                print(f"  - No videos found in folder: {pose_videos_folder}. Skipping.")
                return

            all_segment_features = []
            for video_path in tqdm(videos, unit="video", desc=f"  - Processing videos for '{pose_name}'"):
                feature_tensor, _ = self.segmentor.process_video_cosine_segments(video_path)
                if feature_tensor.shape[0] > 0:
                    all_segment_features.append(feature_tensor)
            
            if not all_segment_features:
                print(f"  - Could not extract any features from videos. Skipping.")
                return

            # Shape becomes (total_frames, num_segments, num_features)
            stacked_features = np.vstack(all_segment_features)
            
            pose_mean = np.mean(stacked_features, axis=0)
            pose_std = np.std(stacked_features, axis=0)
            
            reference_data[pose_name] = {
                "mean": pose_mean.tolist(),
                "std": pose_std.tolist(),
                "config": pose_config
            }
        
        with open(file=self.reference_json_path, mode='w', encoding='utf-8') as file:
            json.dump(reference_data, file, indent=4)
        
        print(f"  - Successfully saved model for '{pose_name}' to '{self.reference_json_path}'.")

    def get_poses_from_video(self, input_video_path):
        """
        Analyzes a video and returns a continuous, frame-by-frame list of scores 
        for all defined poses and their sub-components.
        """
        with open(self.reference_json_path, mode="r", encoding='utf-8') as file:
            reference_data = json.load(file)

        feature_tensor, mask = self.segmentor.process_video_cosine_segments(input_video_path)
        if feature_tensor.shape[0] == 0:
            return []

        all_frame_results = []
        for frame_index, frame_features in enumerate(feature_tensor):
            if not mask[frame_index]:
                all_frame_results.append({}) # Append empty dict for non-detected frames
                continue

            # This dictionary will hold all calculated scores for the current frame
            # before they are structured into the final output format.
            all_pose_scores = {}

            # 1. Calculate scores for all fundamental poses first.
            for pose_name, pose_data in reference_data.items():
                if "mean" in pose_data:  # Identifies it as a fundamental pose
                    config = pose_data["config"]
                    
                    segment_mask = config.get("segment_mask", list(range(len(pose_data["mean"]))))
                    feature_mask = config.get("feature_mask", [True, True, True])

                    score = self._similarity_score(
                        frame_features,
                        pose_data["mean"],
                        pose_data["std"],
                        segment_mask,
                        feature_mask
                    )
                    all_pose_scores[pose_name] = score
            
            # This dictionary will hold the final structured result for the frame.
            frame_scores_structured = {}

            # 2. Structure the output with top-level poses and their sub-scores.
            for pose_name, pose_data in reference_data.items():
                # We only want top-level poses as the main keys in our output
                if pose_data["config"].get("is_sub_pose", False):
                    continue

                config = pose_data["config"]
                
                # Case 1: It's a composite pose
                if "sub_poses" in config:
                    sub_pose_names = config.get("sub_poses", [])
                    sub_scores = {name: all_pose_scores.get(name, 0.0) for name in sub_pose_names}
                    
                    aggregated_score = 0.0
                    if sub_scores:
                        # You can change the aggregation method here if needed (e.g., np.min)
                        aggregated_score = np.mean(list(sub_scores.values()))

                    frame_scores_structured[pose_name] = {
                        "score": aggregated_score,
                        "sub_scores": sub_scores
                    }
                # Case 2: It's a simple, top-level pose
                else:
                    score = all_pose_scores.get(pose_name, 0.0)
                    frame_scores_structured[pose_name] = {
                        "score": score,
                        "sub_scores": {} # No sub-scores for a simple pose
                    }

            all_frame_results.append(frame_scores_structured)

        return all_frame_results
