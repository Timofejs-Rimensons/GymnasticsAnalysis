import json
import numpy as np
import torch
import cv2
from collections import Counter
from repositories.MediapipeSegmentationRepository import MediapipeSegmentationRepository
from services.ClassifyingService import ClassifyingService
from services.VisualisationService import save_visualized_video
from services.PdfReportService import generate_pdf_report
from services.HandstandAnalyticsService import HandstandAnalyticsService
from services.LeapAnalyticsService import LeapAnalyticsService
from services.BoxDetectionService import BoxDetectionService

class ProcessingPipelineService:

    def __init__(self):
        with open("config.json", 'r') as config_file:
            self.config = json.load(config_file)

        self.improvement_needed_treshold = self.config.get("improvement_needed_treshold", 0.7)
        self.segmentation_repository = MediapipeSegmentationRepository()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # 1. Initialize classification service ONCE
        # Using window_size=20 as requested
        self.classifier = ClassifyingService(
            window_size=20,
            device=self.device,
            verbose=True
        )

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
        corrected_labels = list(labels)

        if exercise_name == 'handstand':
            swing_handstand_indices = [i for i, label in enumerate(labels) if label in ['Swing', 'Handstand']]
            if swing_handstand_indices:
                mean_index = np.mean(swing_handstand_indices)
                pose_names = self.config['models']['handstand']['poses']
                starting_pose = pose_names[0]
                landing_pose = pose_names[-1]

                for i, label in enumerate(corrected_labels):
                    if i < mean_index and label == landing_pose:
                        corrected_labels[i] = starting_pose
                    elif i > mean_index and label == starting_pose:
                        corrected_labels[i] = landing_pose

        label_counts = Counter(corrected_labels)
        label_avg_positions = {label: np.mean([i for i, l in enumerate(corrected_labels) if l == label]) for label in set(corrected_labels)}
        sorted_labels_by_pos = sorted(label_avg_positions.keys(), key=lambda x: label_avg_positions[x])

        grouped_labels = []
        for label in sorted_labels_by_pos:
            grouped_labels.extend([label] * label_counts[label])

        return grouped_labels

    def analyze_video(self, input_video_path: str, output_video_path: str, output_pdf_path: str, output_json_path: str, exercise_name: str, status_json_path: str):
        input_video_path = str(input_video_path)
        output_video_path = str(output_video_path)
        output_pdf_path = str(output_pdf_path)
        output_json_path = str(output_json_path)
        status_json_path = str(status_json_path)

        self._update_status(status_json_path, "processing", 0.1)

        model_config = self.config['models'].get(exercise_name)
        if not model_config:
            raise ValueError(f"Exercise '{exercise_name}' not found in config.")

        # 2. Load the specific model weights (Standalone .pt or .pth)
        # This uses the same classifier instance initialized in __init__
        self.classifier.load_model(model_config['model_path'])
        pose_labels = model_config['poses']

        if exercise_name == 'handstand':
            analytics_service_class = HandstandAnalyticsService
            pose_config = self.config.get('pose_criteria', {}).get('handstand', {})
        elif exercise_name in ['straddle_jump']:
            analytics_service_class = LeapAnalyticsService
            pose_config = self.config.get('pose_criteria', {}).get('straddle_jump', {})
        else:
            raise ValueError(f"Unknown exercise type: {exercise_name}")

        analytics_service = analytics_service_class(config=pose_config)

        self._update_status(status_json_path, "processing", 0.2)

        # 3. Get features and frames
        frames_data, feature_tensor, _ = self.segmentation_repository.process_video_stgcn(input_video_path)
        _, world_pose_tensor, _ = self.segmentation_repository.process_video(input_video_path)

        if feature_tensor is None or feature_tensor.shape[1] == 0:
            self._update_status(status_json_path, "completed", 1)
            return

        # 3b. For straddle_jump, detect vault box positions
        box_edge_world_coords = []
        if exercise_name in ['straddle_jump']:
            box_detector = BoxDetectionService(model_path="best.pt")
            video_capture = cv2.VideoCapture(input_video_path)

            frame_idx = 0
            while video_capture.isOpened():
                success, frame = video_capture.read()
                if not success:
                    break

                # Detect box edge in pixel coordinates
                box_edge_px = box_detector.detect_box_edge(frame)

                # Convert pixel x-coordinate to world coordinate using shoulder width as reference
                if box_edge_px is not None and frame_idx < len(world_pose_tensor):
                    world_pose = world_pose_tensor[frame_idx]

                    # Get shoulder positions in world coordinates (meters)
                    left_shoulder = world_pose[1]  # Joint index 1
                    right_shoulder = world_pose[2]  # Joint index 2

                    # Use frame center as reference
                    frame_width = frame.shape[1]
                    frame_center_x = frame_width / 2

                    # Convert box edge to world x-coordinate relative to frame center
                    # Assuming average body is about 0.5m wide and takes up ~1/3 of frame width
                    pixels_per_meter = frame_width / 1.5  # Rough estimate
                    box_edge_world = (box_edge_px - frame_center_x) / pixels_per_meter
                else:
                    box_edge_world = None

                box_edge_world_coords.append(box_edge_world)
                frame_idx += 1

            video_capture.release()

        self._update_status(status_json_path, "processing", 0.5)

        # 4. Predict using the pre-loaded classifier
        # predict_video handles the sliding window internally
        raw_labels = self.classifier.predict_video(feature_tensor, class_names=pose_labels)
        processed_labels = self._process_labels(raw_labels, exercise_name)

        self._update_status(status_json_path, "processing", 0.7)

        # 5. Perform analytics
        all_scores = {label: [] for label in pose_labels}
        analytics_per_frame = []

        # For handstand, we also track HandPlacement separately
        hand_placement_analytics = []
        if exercise_name == 'handstand' and 'HandPlacement' not in all_scores:
            all_scores['HandPlacement'] = []

        for i, pose_name in enumerate(processed_labels):
            analytics_result = None
            if i < len(world_pose_tensor):
                current_world_pose = world_pose_tensor[i]

                # For straddle_jump in Flight1 phase, pass box edge coordinate
                if exercise_name in ['straddle_jump'] and pose_name == 'Flight1':
                    box_edge_x = box_edge_world_coords[i] if i < len(box_edge_world_coords) else None
                    analytics_result = analytics_service.analyze_pose(current_world_pose, pose_name, box_edge_x=box_edge_x)
                else:
                    analytics_result = analytics_service.analyze_pose(current_world_pose, pose_name)

                if analytics_result and 'score' in analytics_result:
                    all_scores[pose_name].append(analytics_result['score'])

                # For handstand frames, also analyze hand placement separately
                if exercise_name == 'handstand' and pose_name == 'Handstand':
                    hand_placement_result = analytics_service.analyze_pose(current_world_pose, 'HandPlacement')
                    if hand_placement_result and 'score' in hand_placement_result:
                        all_scores['HandPlacement'].append(hand_placement_result['score'])
                        hand_placement_analytics.append(hand_placement_result)

            analytics_per_frame.append(analytics_result)

        # 6. Aggregate analytics
        analytics_per_pose = {}
        for pose_name in pose_labels:
            pose_specific_analytics = [res for i, res in enumerate(analytics_per_frame) if processed_labels[i] == pose_name and res]
            if pose_specific_analytics:
                analytics_per_pose[pose_name] = analytics_service.aggregate_frame_feedback(pose_specific_analytics)

        # Aggregate HandPlacement analytics for handstand
        if exercise_name == 'handstand' and hand_placement_analytics:
            analytics_per_pose['HandPlacement'] = analytics_service.aggregate_frame_feedback(hand_placement_analytics)

        self._update_status(status_json_path, "saving", 0.9)

        # 7. Save results and annotated video
        self._structure_and_save_results(all_scores, analytics_per_pose, output_json_path, output_pdf_path)

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
