import numpy as np
import json
from pathlib import Path
from tqdm import tqdm
import os

from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository

class PoseScoringService:
    """
    A service for fitting pose models from reference videos and scoring new videos
    against those models.
    """
    def __init__(self):
        """
        Initializes the PoseScoringService, loading configuration and setting up
        dependencies.
        """
        with open("config.json", 'r') as config_file:
            config = json.load(config_file)
            
        self.exercises = config["exercises"]
        self.reference_json_path = config["model_in_use"]
        self.segmentation_repository = MediapipeSegmentationRepository()
        self.video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]

    def _get_video_files(self, folder_path):
        """
        Retrieves a list of video files from a specified folder.

        Args:
            folder_path (str): The path to the folder containing video files.

        Returns:
            list: A list of strings, where each string is the path to a video file.
        """
        video_folder_path = Path(folder_path)
        return [
            str(path)
            for path in video_folder_path.iterdir()
            if path.is_file() and path.suffix.lower() in self.video_extensions
        ]

    @staticmethod
    def _calculate_similarity_score(frame_features, pose_mean, pose_std, segment_mask, feature_mask):
        """
        Calculates a similarity score between a frame's features and a reference pose.

        The score is based on the Z-score distance between the frame's features
        and the mean of the reference pose's features, normalized by the standard
        deviation.

        Args:
            frame_features (np.ndarray): The feature tensor for a single frame.
            pose_mean (np.ndarray): The mean feature tensor of the reference pose.
            pose_std (np.ndarray): The standard deviation of the features of the
                                   reference pose.
            segment_mask (list): A mask to select which body segments to include
                                 in the score calculation.
            feature_mask (list): A mask to select which features to include in
                                 the score calculation.

        Returns:
            float: The similarity score, ranging from 0 to 1.
        """
        frame_features = np.asarray(frame_features)
        pose_mean = np.asarray(pose_mean)
        pose_std = np.asarray(pose_std)
        segment_mask = np.asarray(segment_mask)
        feature_mask = np.asarray(feature_mask)

        relevant_features = frame_features[segment_mask][:, feature_mask]
        relevant_mean = pose_mean[segment_mask][:, feature_mask]
        relevant_std = pose_std[segment_mask][:, feature_mask]
        
        z_distance = (relevant_features - relevant_mean) / (relevant_std + 1e-8)
        mean_absolute_z_distance = np.mean(np.abs(z_distance))
        
        return float(np.exp(-mean_absolute_z_distance))

    def fit(self, video_folder_path, pose_name, exercise_name, pose_config={}):
        """
        Fits a model for a given pose and saves its configuration and statistical data.

        This method processes a collection of reference videos for a specific pose,
        calculates the mean and standard deviation of the pose features, and saves
        this data to a JSON file for later use in scoring.

        Args:
            video_folder_path (str): The path to the folder containing reference videos.
            pose_name (str): The name of the pose to be fitted.
            exercise_name (str): The name of the exercise to which the pose belongs.
            pose_config (dict, optional): A dictionary containing configuration
                                          for the pose, such as masks or sub-pose
                                          definitions. Defaults to {}.
        """
        print(f"Fitting model for pose: '{pose_name}'...")
        if not os.path.exists(self.reference_json_path):
            with open(self.reference_json_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
        
        with open(file=self.reference_json_path, mode='r', encoding='utf-8') as reference_file:
            reference_data = json.load(reference_file)
            
        if exercise_name not in reference_data:
            reference_data[exercise_name] = {}

        if "sub_poses" in pose_config:
            reference_data[exercise_name][pose_name] = {"config": pose_config}
            print(f"  - Composite pose detected. Aggregates: {pose_config['sub_poses']}")
        else:
            video_files = self._get_video_files(video_folder_path)
            if not video_files:
                print(f"  - No videos found in folder: {video_folder_path}. Skipping.")
                return

            all_segment_features = []
            for video_path in tqdm(video_files, unit="video", desc=f"  - Processing videos for '{pose_name}'"):
                _, feature_tensor, _ = self.segmentation_repository.process_video_cosine_segments(video_path)
                if feature_tensor.shape[0] > 0:
                    all_segment_features.append(feature_tensor)
            
            if not all_segment_features:
                print(f"  - Could not extract any features from videos. Skipping.")
                return

            stacked_features = np.vstack(all_segment_features)
            
            pose_mean = np.mean(stacked_features, axis=0)
            pose_std = np.std(stacked_features, axis=0)
            
            reference_data[exercise_name][pose_name] = {
                "mean": pose_mean.tolist(),
                "std": pose_std.tolist(),
                "config": pose_config
            }
        
        with open(file=self.reference_json_path, mode='w', encoding='utf-8') as reference_file:
            json.dump(reference_data, reference_file, indent=4)
        
        print(f"  - Successfully saved model for '{pose_name}' to '{self.reference_json_path}'.")

    def get_poses_from_video(self, input_video_path, exercise_name):
        """
        Analyzes a video and scores each frame against all poses of a given exercise.

        This method processes a video, calculates similarity scores for each frame
        against pre-fitted pose models, and returns a structured list of these scores.

        Args:
            input_video_path (str): The path to the video to be analyzed.
            exercise_name (str): The name of the exercise to score against.

        Returns:
            A tuple containing:
            - all_frame_scores (list): A list of dictionaries, where each
              dictionary contains the scores for all poses in a single frame.
            - frames (list): A list of frame data dictionaries from the
              segmentation repository.
        """
        if not os.path.exists(self.reference_json_path):
            with open(self.reference_json_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
                
        with open(self.reference_json_path, mode="r", encoding='utf-8') as reference_file:
            reference_data = json.load(reference_file).get(exercise_name, {})

        frames, feature_tensor, mask = self.segmentation_repository.process_video_cosine_segments(input_video_path)
        if feature_tensor.shape[0] == 0:
            return [], frames

        all_frame_scores = []
        for frame_index, current_frame_features in enumerate(feature_tensor):
            if not mask[frame_index]:
                all_frame_scores.append({}) # Append empty dict for non-detected frames
                continue

            all_pose_scores = {}

            # 1. Calculate scores for all fundamental poses first.
            for pose_name, pose_data in reference_data.items():
                if "mean" in pose_data:  # Identifies it as a fundamental pose
                    config = pose_data["config"]
                    
                    segment_mask = config.get("segment_mask", list(range(len(pose_data["mean"]))))
                    feature_mask = config.get("feature_mask", [True, True, True])

                    score = self._calculate_similarity_score(
                        current_frame_features,
                        pose_data["mean"],
                        pose_data["std"],
                        segment_mask,
                        feature_mask
                    )
                    all_pose_scores[pose_name] = score
            
            frame_scores_structured = {}

            # 2. Structure the output with top-level poses and their sub-scores.
            for pose_name, pose_data in reference_data.items():
                if pose_data["config"].get("is_sub_pose", False):
                    continue

                config = pose_data["config"]
                
                if "sub_poses" in config:
                    sub_pose_names = config.get("sub_poses", [])
                    sub_scores = {name: all_pose_scores.get(name, 0.0) for name in sub_pose_names}
                    
                    aggregated_score = 0.0
                    if sub_scores:
                        aggregated_score = np.mean(list(sub_scores.values()))

                    frame_scores_structured[pose_name] = {
                        "score": aggregated_score,
                        "sub_scores": sub_scores
                    }
                else:
                    score = all_pose_scores.get(pose_name, 0.0)
                    frame_scores_structured[pose_name] = {
                        "score": score,
                        "sub_scores": {}
                    }
            
            # Determine phase by max score
            if frame_scores_structured:
                top_pose = max(frame_scores_structured, key=lambda p: frame_scores_structured[p]['score'])
                frame_scores_structured['phase'] = top_pose
            else:
                frame_scores_structured['phase'] = "no_pose"
            
            all_frame_scores.append(frame_scores_structured)

        return all_frame_scores, frames
