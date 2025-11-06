import cv2
import mediapipe as mp
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

class MediapipeSegmentationService:
    
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

    def normalize_landmarks_3d_with_reference(self, landmarks, frame_width, frame_height):
        """
        Normalize selected pose landmarks in 3D relative to person bounding box.
        Returns:
            - normalized_coords: flattened array of landmarks [0,1]
            - reference_point: midpoint of hips in pixels
            - bbox_size: width and height of bounding box in pixels
        """
        if landmarks is None:
            return None, None, None, None

        selected_indices = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

        # Convert normalized MP coordinates to pixel coordinates
        coords = np.array([[landmarks.landmark[i].x * frame_width,
                            landmarks.landmark[i].y * frame_height,
                            landmarks.landmark[i].z]  # keep z for completeness
                           for i in selected_indices])

        # Reference point: midpoint of hips
        left_hip = coords[7]
        right_hip = coords[8]
        reference_point = (left_hip + right_hip) / 2

        coords_shifted = coords - reference_point

        # Bounding box in shifted coordinates
        min_xy = coords_shifted[:, :2].min(axis=0)
        max_xy = coords_shifted[:, :2].max(axis=0)
        bbox_size = max_xy - min_xy
        bbox_size[bbox_size == 0] = 1.0

        # Normalize
        normalized_coords = coords_shifted.copy()
        normalized_coords[:, 0] = (coords_shifted[:, 0] - min_xy[0]) / bbox_size[0]
        normalized_coords[:, 1] = (coords_shifted[:, 1] - min_xy[1]) / bbox_size[1]

        # Return min_xy as well
        return normalized_coords.flatten(), reference_point, bbox_size, min_xy

    def segmentate_video(self, video_path: str) -> list:
        """
        Returns a list of dicts per frame containing:
            - normalized landmarks
            - reference point (mid-hip in pixels)
            - bbox size (width, height in pixels)
        """
        segment_per_frames = []

        cap = cv2.VideoCapture(video_path)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        with self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break

                frame.flags.writeable = False
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(frame_rgb)

                normalized_landmarks, reference_point, bbox_size, min_xy = self.normalize_landmarks_3d_with_reference(
                    results.pose_landmarks, frame_width, frame_height
                )

                segment_per_frames.append({
                    "landmarks": normalized_landmarks,
                    "reference": reference_point,
                    "bbox_size": bbox_size,
                    "min_xy": min_xy
                })

            cap.release()
        return segment_per_frames

    def save_visualized_video(self, video_path: str, output_path: str, positions: list):
        """
        Draw normalized landmarks using reference point and bbox to reconstruct pixel positions.
        Saves annotated video to disk.
        """
        
        connections = [
            (0,1),(0,2),
            (1,2),
            (1,3),(2,4),
            (3,5),(4,6),
            (1,7),(2,8),
            (7,8),
            (7,9),(8,10),
            (9,11),(10,12)
        ]

        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

        frame_idx = 0
        while cap.isOpened() and frame_idx < len(positions):
            success, frame = cap.read()
            if not success:
                break

            frame_data = positions[frame_idx]
            landmarks = frame_data["landmarks"]
            reference = frame_data["reference"]
            bbox_size = frame_data["bbox_size"]

            if landmarks is not None:
                coords = np.array(landmarks).reshape(-1, 3)
                
                # Reconstruct pixel positions
                pixel_coords = coords.copy()
                min_xy = frame_data["min_xy"]
                pixel_coords[:, 0] = coords[:, 0] * bbox_size[0] + min_xy[0] + reference[0]
                pixel_coords[:, 1] = coords[:, 1] * bbox_size[1] + min_xy[1] + reference[1]
                pixel_coords = pixel_coords.astype(int)[:, :2]

                for x, y in pixel_coords:
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                    
                for start, end in connections:
                    x1, y1 = pixel_coords[start]
                    x2, y2 = pixel_coords[end]
                    cv2.line(frame, (x1, y1), (x2, y2), (200, 200, 200), 2)

            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()
        print(f"Video saved to {output_path}")


if __name__ == "__main__":
    segmentor = MediapipeSegmentationService()
    positions = segmentor.segmentate_video("data/dataset/handstand/vids/img_h1.mp4")
    segmentor.save_visualized_video("data/dataset/handstand/vids/img_h1.mp4", 
                                     "test_output.mp4", positions)
