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
        
    def analyze_video(self, input_video_path, output_video_path, output_pdf_path, output_json_path, exercise_name):
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
            return
        
        total_scores = {}
        for frame_scores in pose_scores_per_frame:
            for pose_name, data in frame_scores.items():
                if pose_name not in total_scores:
                    total_scores[pose_name] = 0
                total_scores[pose_name] += data['score']

        score_sum = sum(total_scores.values())
        if score_sum > 0:
            normalized_total_scores = {k: v / score_sum for k, v in total_scores.items()}
        else:
            normalized_total_scores = total_scores

        with open(output_json_path, 'w') as json_file:
            json.dump(normalized_total_scores, json_file, indent=4)
            
        pose_labels = []
        for frame_scores in pose_scores_per_frame:
            label = ""
            for pose_name, data in frame_scores.items():
                label += f"{pose_name}: {data['score']:.2f}"
                if data['sub_scores']:
                    label += " | "
                    label += " | ".join([f"{sub_pose}: {sub_score:.2f}" for sub_pose, sub_score in data['sub_scores'].items()])
                label += "\n"
            pose_labels.append(label)

        save_visualized_video(output_video_path, frames, input_video_path, pose_labels)

        with open(output_pdf_path, 'w') as pdf_file:
            pass