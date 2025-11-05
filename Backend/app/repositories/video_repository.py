from typing import List, Tuple

import cv2
import numpy as np

from app.models.handstand_models import FrameFeatures


class VideoRepository:
    """
    Handles all video I/O + raw pose feature extraction.
    """

    def __init__(self, pose):
        """
        pose: an initialized MediaPipe Pose object
        """
        self.pose = pose

    def extract_pose_features(self, video_path: str) -> Tuple[List[FrameFeatures], float]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        frames: List[FrameFeatures] = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(image_rgb)

            wrist_y = hip_y = ankle_y = np.nan
            torso_angle = np.nan
            hip_line_angle = np.nan

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark

                left_wrist = np.array([lm[15].x, lm[15].y])
                right_wrist = np.array([lm[16].x, lm[16].y])
                left_hip = np.array([lm[23].x, lm[23].y])
                right_hip = np.array([lm[24].x, lm[24].y])
                left_ankle = np.array([lm[27].x, lm[27].y])
                right_ankle = np.array([lm[28].x, lm[28].y])
                left_shoulder = np.array([lm[11].x, lm[11].y])
                right_shoulder = np.array([lm[12].x, lm[12].y])

                wrist_y = float(np.mean([left_wrist[1], right_wrist[1]]))
                hip_y = float(np.mean([left_hip[1], right_hip[1]]))
                ankle_y = float(np.mean([left_ankle[1], right_ankle[1]]))

                shoulder_mid = (left_shoulder + right_shoulder) / 2.0
                hip_mid = (left_hip + right_hip) / 2.0
                ankle_mid = (left_ankle + right_ankle) / 2.0

                torso_angle = self._angle_with_vertical(hip_mid, shoulder_mid)
                hip_line_angle = self._angle_three_points(
                    shoulder_mid, hip_mid, ankle_mid
                )

            frames.append(
                FrameFeatures(
                    frame_idx=frame_idx,
                    time=frame_idx / fps if fps > 0 else 0.0,
                    wrist_y=wrist_y,
                    hip_y=hip_y,
                    ankle_y=ankle_y,
                    torso_angle=torso_angle,
                    hip_line_angle=hip_line_angle,
                )
            )

            frame_idx += 1

        cap.release()
        return frames, fps

    def _angle_with_vertical(self, p_base, p_top) -> float:
        v = p_top - p_base
        vertical = np.array([0.0, -1.0])
        dot = float(np.dot(v, vertical))
        denom = float(np.linalg.norm(v) * np.linalg.norm(vertical) + 1e-6)
        cosang = np.clip(dot / denom, -1.0, 1.0)
        return float(np.degrees(np.arccos(cosang)))

    def _angle_three_points(self, a, b, c) -> float:
        ba = a - b
        bc = c - b
        denom = float(np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        cosang = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
        return float(np.degrees(np.arccos(cosang)))
