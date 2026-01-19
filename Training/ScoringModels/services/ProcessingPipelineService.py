import json
import os
import numpy as np
from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository
from services.PoseScoringService import PoseScoringService
from services.VisualisationService import save_visualized_video
from services.PdfReportService import generate_pdf_report
from ScoringModels.services.ModelService import ModelService

class ProcessingPipelineService:
    
    def __init__(self):
        with open("config.json", 'r') as config_file:
            config = json.load(config_file)
        
        self.models = config.get("models", {})
        self.improvement_needed_treshold = config.get("improvement_needed_treshold", 0)
        self.segmentation_repository = MediapipeSegmentationRepository()
        self.pose_scoring_service = PoseScoringService()

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

    def _structure_and_save_results(self, pose_scores_per_frame, output_json_path, output_pdf_path):
        all_poses = {}
        for frame_scores in pose_scores_per_frame:
            for pose_name, data in frame_scores.items():
                if pose_name == 'phase':
                    continue
                if 'sub_scores' in data and data['sub_scores']:
                    for sub_pose, sub_score in data['sub_scores'].items():
                        if sub_pose not in all_poses:
                            all_poses[sub_pose] = []
                        all_poses[sub_pose].append(sub_score)
                else:
                    if pose_name not in all_poses:
                        all_poses[pose_name] = []
                    all_poses[pose_name].append(data.get('score', 0))

        
        pose_scores = {pose: np.mean(scores) for pose, scores in all_poses.items()}
        
        scores = list(pose_scores.values())
        if not scores:
            overall_score_raw = 0
            max_raw_score = 1
        else:
            overall_score_raw = sum(scores)
            max_raw_score = len(pose_scores)

        target_max_score = 100.0
        individual_pose_max_score = target_max_score / max_raw_score
        
        overall_score = (overall_score_raw / max_raw_score) * target_max_score if max_raw_score > 0 else 0
        percentage = overall_score 

        pose_categories = []
        for pose, score in pose_scores.items():
            improvement_needed = bool(score < self.improvement_needed_treshold)
            
            pose_categories.append({
                "name": pose,
                "score": round(score * individual_pose_max_score),
                "max_score": round(individual_pose_max_score),
                "description": "Placeholder description.",
                "improvement_needed": improvement_needed
            })
            
        # pose_categories.append({
        #     "name": "Space for improvement",
        #     "score": round(100 - overall_score),
        #     "max_score": 100,
        #     "description": "Placeholder description.",
        #     "improvement_needed": bool(True)
        # })

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

    def analyze_video(self, input_video_path: str, output_video_path: str, output_pdf_path: str, output_json_path: str, exercise_name: str, status_json_path: str):
        # Convert Path objects to strings if necessary
        input_video_path = str(input_video_path)
        output_video_path = str(output_video_path)
        output_pdf_path = str(output_pdf_path)
        output_json_path = str(output_json_path)
        status_json_path = str(status_json_path)
        
        classifier = PoseClassifier(num_classes=4, window_size=24, model_path='./model_weights/gruClassifier7821.pth')
        
        if not pose_scores_per_frame:
            with open(output_json_path, 'w') as json_file:
                json.dump({}, json_file)
            with open(output_pdf_path, 'w') as pdf_file:
                generate_pdf_report(analysis={}, output_path=output_pdf_path)
            self._update_status(status_json_path, "completed", 1)
            return
        
        self._structure_and_save_results(pose_scores_per_frame, output_json_path, output_pdf_path)

        frame_annotations = []
        for frame_scores in pose_scores_per_frame:
            top_pose_name = frame_scores.get('phase')
            annotation = {"label": "None", "segment_scores": None}
            
            if top_pose_name and top_pose_name != "no_pose":
                top_pose_data = frame_scores.get(top_pose_name)
                if top_pose_data:
                    label = f"{top_pose_name}: {top_pose_data.get('score', 0):.2f}"
                    
                    sub_scores = top_pose_data.get('sub_scores')
                    if sub_scores:
                        label += " | " + " | ".join([f"{name}: {score:.2f}" for name, score in sub_scores.items()])
                    
                    annotation["label"] = label
                    annotation["segment_scores"] = top_pose_data.get("segment_scores")

            frame_annotations.append(annotation)

        save_visualized_video(output_video_path, frames, input_video_path, frame_annotations=frame_annotations)
        
        self._update_status(status_json_path, "completed", 1)