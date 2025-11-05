import cv2
import mediapipe as mp
import os
from typing import List, Dict
from app.config import settings

class VideoProcessor:
    """
    Process video and extract pose landmarks using Mediapipe.
    """
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=settings.POSE_MODEL_COMPLEXITY,
            min_detection_confidence=settings.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.MIN_TRACKING_CONFIDENCE
        )

    def process_video(self, video_path: str) -> List[Dict]:
        """
        Process the video and extract pose landmarks for each frame.

        Args:
            video_path (str): Path to the input video file.
        Returns:
            List[Dict]: List of pose landmarks for each frame.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        landmarks_data = []
        frame_count = 0
        max_frames = 1000  # Safety limit to prevent infinite processing

        try:
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                #convert the BGR image to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                #process frame
                results = self.pose.process(rgb_frame)

                if results.pose_landmarks:
                    #extract landmarks
                    landmarks = self._extract_landmarks(results.pose_landmarks)
                    landmarks['frame_number'] = frame_count
                    landmarks_data.append(landmarks)

                frame_count += 1

        finally:
            cap.release()
            self.pose.close()

        print(f"Processed {frame_count} frames, detected pose in {len(landmarks_data)} frames")
        return landmarks_data
    
    def _extract_landmarks(self, pose_landmarks) -> Dict:
        """
        Extract key landmarks as dictionary
        
        MediaPipe Pose Landmarks (33 points):
        0: nose, 11-12: shoulders, 13-14: elbows, 15-16: wrists,
        23-24: hips, 25-26: knees, 27-28: ankles, etc.
        """
        landmarks = {}
        for idx, landmark in enumerate(pose_landmarks.landmark):
            landmarks[f"landmark_{idx}"] = {
                "x": landmark.x,
                "y": landmark.y,
                "z": landmark.z,
                "visibility": landmark.visibility
            }
        return landmarks