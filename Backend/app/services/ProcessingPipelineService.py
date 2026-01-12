import json
import os
from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository
from services.PoseScoringService import PoseScoringService
from services.VisualisationService import save_visualized_video

class ProcessingPipelineService:
    
    def __init__(self):
        """
        Initializes the ProcessingPipelineService.

        This service orchestrates the video analysis pipeline by initializing the
        necessary services for pose scoring and visualization.
        """
        self.segmentation_repository = MediapipeSegmentationRepository()
        self.pose_scoring_service = PoseScoringService()

    def _update_status(self, status_json_path: str, status: str, progress: float):
        """Safely updates the status JSON file, preserving existing content."""
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
        
    def analyze_video(self: str, input_video_path: str, output_video_path: str, output_pdf_path: str, output_json_path: str, exercise_name: str, status_json_path: str):
        """
        Analyzes a video, generates pose scores, and creates visualization files.

        This method coordinates the entire analysis pipeline, including pose
        estimation, scoring, and the generation of output files such as a
        visualization video, a JSON file with scores, and a placeholder PDF.

        Args:
            input_video_path (str): Path to the input video file.
            output_video_path (str): Path to save the output video visualization.
            output_pdf_path (str): Path to save the output PDF report.
            output_json_path (str): Path to save the JSON file with pose scores.
            exercise_name (str): The name of the exercise being analyzed.
        """
        
        
        pose_scores_per_frame, frames = self.pose_scoring_service.get_poses_from_video(input_video_path, exercise_name)
        
        if not pose_scores_per_frame:
            with open(output_json_path, 'w') as json_file:
                json.dump({}, json_file)
            with open(output_pdf_path, 'w') as pdf_file:
                pass
            self._update_status(status_json_path, "completed", 1)
            return
        
        total_scores = {}
        for frame_scores in pose_scores_per_frame:
            for pose_name, data in frame_scores.items():
                if isinstance(data, dict):
                    if pose_name not in total_scores:
                        total_scores[pose_name] = 0
                    total_scores[pose_name] += data.get('score', 0)

        score_sum = sum(total_scores.values())
        if score_sum > 0:
            normalized_total_scores = {k: v / score_sum for k, v in total_scores.items()}
        else:
            normalized_total_scores = total_scores

        with open(output_json_path, 'w') as json_file:
            json.dump(normalized_total_scores, json_file, indent=4)

        pose_labels = []
        for frame_scores in pose_scores_per_frame:
            def get_score(item):
                if isinstance(item[1], dict):
                    return item[1].get("score", 0)
                return 0

            sorted_poses = sorted(frame_scores.items(), key=get_score, reverse=True)
            
            if not sorted_poses:
                pose_labels.append("None")
                continue

            best_pose = sorted_poses[0]
            
            if not isinstance(best_pose[1], dict) or 'score' not in best_pose[1]:
                 pose_labels.append("None")
                 continue

            data = best_pose[1]
            label = ""
            label += f"{best_pose[0]}: {data['score']:.2f}"
            if data.get('sub_scores'):
                label += " | "
                label += " | ".join([f"{sub_pose}: {sub_score:.2f}" for sub_pose, sub_score in data['sub_scores'].items()])
            label += "\n"
            pose_labels.append(label)

        save_visualized_video(output_video_path, frames, input_video_path, pose_labels)

        with open(output_pdf_path, 'w') as pdf_file:
            pass
        
        self._update_status(status_json_path, "completed", 1)
        