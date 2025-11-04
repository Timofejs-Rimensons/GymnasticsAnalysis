import cv2
import numpy as np
import mediapipe as mp


class HandstandPhaseService:
    """
    Simple service to:
    - read a video
    - run MediaPipe Pose
    - compute basic features (heights + angles)
    - label each frame into phases:
        starting, upswing, hand_placement, body_position, landing_finishing
    - group frames into time segments
    """

    def __init__(self,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5,
                 model_complexity=1):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    # ---------- PUBLIC MAIN FUNCTION ----------

    def analyze_video(self, video_path):
        """
        Main entry.
        Returns:
            segments: list of dicts with phase, start/end frame & time
            frames:   list of per-frame dicts (features + phase label)
        """
        frames, fps = self._extract_pose_features(video_path)
        if not frames or fps <= 0:
            return [], []

        labeled_frames = self._classify_frames(frames)
        segments = self._group_segments(labeled_frames)

        return segments, labeled_frames

    # ---------- INTERNAL HELPERS ----------

    def _extract_pose_features(self, video_path):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        frames = []
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

                # Main points (normalized 0–1)
                left_wrist = np.array([lm[15].x, lm[15].y])
                right_wrist = np.array([lm[16].x, lm[16].y])
                left_hip = np.array([lm[23].x, lm[23].y])
                right_hip = np.array([lm[24].x, lm[24].y])
                left_ankle = np.array([lm[27].x, lm[27].y])
                right_ankle = np.array([lm[28].x, lm[28].y])
                left_shoulder = np.array([lm[11].x, lm[11].y])
                right_shoulder = np.array([lm[12].x, lm[12].y])

                wrist_y = np.mean([left_wrist[1], right_wrist[1]])
                hip_y = np.mean([left_hip[1], right_hip[1]])
                ankle_y = np.mean([left_ankle[1], right_ankle[1]])

                shoulder_mid = (left_shoulder + right_shoulder) / 2.0
                hip_mid = (left_hip + right_hip) / 2.0
                ankle_mid = (left_ankle + right_ankle) / 2.0

                # torso_angle: hip->shoulder vs vertical
                torso_angle = self._angle_with_vertical(hip_mid, shoulder_mid)

                # hip_line_angle: shoulder–hip–ankle (straight line ~ 180°)
                hip_line_angle = self._angle_three_points(shoulder_mid,
                                                          hip_mid,
                                                          ankle_mid)

            frames.append({
                "frame_idx": frame_idx,
                "time": frame_idx / fps if fps > 0 else 0.0,
                "wrist_y": wrist_y,
                "hip_y": hip_y,
                "ankle_y": ankle_y,
                "torso_angle": torso_angle,
                "hip_line_angle": hip_line_angle,
            })

            frame_idx += 1

        cap.release()
        return frames, fps

    def _angle_with_vertical(self, p_base, p_top):
        """
        Angle between vector (base->top) and vertical axis.
        Lower value = more vertical.
        """
        v = p_top - p_base               # y goes down in image coords
        vertical = np.array([0.0, -1.0]) # "up" direction
        dot = np.dot(v, vertical)
        denom = (np.linalg.norm(v) * np.linalg.norm(vertical) + 1e-6)
        cosang = np.clip(dot / denom, -1.0, 1.0)
        return np.degrees(np.arccos(cosang))

    def _angle_three_points(self, a, b, c):
        """
        Angle at point b for triangle a-b-c.
        Returns degrees [0, 180].
        """
        ba = a - b
        bc = c - b
        denom = (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        cosang = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
        return np.degrees(np.arccos(cosang))

    def _classify_frames(self, frames):
        # Use ankle_y to estimate "floor" (largest y = closest to bottom)
        ankle_vals = np.array([f["ankle_y"] for f in frames
                               if not np.isnan(f["ankle_y"])])
        if len(ankle_vals) == 0:
            # no pose – everything unknown
            for f in frames:
                f["phase"] = "unknown"
            return frames

        floor_y = float(np.nanmax(ankle_vals))

        for f in frames:
            ay = f["ankle_y"]
            wy = f["wrist_y"]
            hy = f["hip_y"]
            torso_angle = f["torso_angle"]
            hip_line_angle = f["hip_line_angle"]

            if any(np.isnan(v) for v in [ay, wy, hy, torso_angle, hip_line_angle]):
                phase = "unknown"
            else:
                # basic signals
                feet_on_floor = ay > (floor_y - 0.03)
                hands_on_floor = wy > (floor_y - 0.03)
                feet_above_hips = ay < hy       # legs higher than hips
                torso_vertical = torso_angle < 25.0
                body_straight = abs(hip_line_angle - 180.0) < 25.0

                # simple phase rules
                if feet_on_floor and not hands_on_floor and torso_vertical:
                    phase = "starting"
                elif not hands_on_floor and not feet_above_hips:
                    phase = "upswing"
                elif hands_on_floor and not feet_above_hips:
                    phase = "hand placement"
                elif hands_on_floor and feet_above_hips and body_straight:
                    phase = "handstand position"
                else:
                    phase = "landing position"

            f["phase"] = phase

        return frames

    def _group_segments(self, labeled_frames):
        if not labeled_frames:
            return []

        segments = []
        current_phase = labeled_frames[0]["phase"]
        start_idx = 0

        for i in range(1, len(labeled_frames)):
            phase = labeled_frames[i]["phase"]
            if phase != current_phase:
                segments.append({
                    "phase": current_phase,
                    "start_frame": labeled_frames[start_idx]["frame_idx"],
                    "end_frame": labeled_frames[i - 1]["frame_idx"],
                    "start_time": labeled_frames[start_idx]["time"],
                    "end_time": labeled_frames[i - 1]["time"],
                })
                current_phase = phase
                start_idx = i

        # last segment
        segments.append({
            "phase": current_phase,
            "start_frame": labeled_frames[start_idx]["frame_idx"],
            "end_frame": labeled_frames[-1]["frame_idx"],
            "start_time": labeled_frames[start_idx]["time"],
            "end_time": labeled_frames[-1]["time"],
        })

        return segments

    def close(self):
        self.pose.close()
