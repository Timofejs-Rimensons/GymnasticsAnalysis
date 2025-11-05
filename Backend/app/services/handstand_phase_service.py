from typing import List, Tuple

import mediapipe as mp
import numpy as np

from app.models.handstand_models import FrameFeatures, PhaseSegment
from app.repositories.video_repository import VideoRepository


class HandstandPhaseService:
    """
    Orchestrates:
    - reading features from repository
    - classifying frames into phases
    - grouping into segments
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
    ):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.video_repo = VideoRepository(self.pose)

    # ---------- PUBLIC API ----------

    def analyze_video(
        self, video_path: str
    ) -> Tuple[List[PhaseSegment], List[FrameFeatures]]:
        frames, fps = self.video_repo.extract_pose_features(video_path)
        if not frames or fps <= 0:
            return [], []

        labeled_frames = self._classify_frames(frames)
        segments = self._group_segments(labeled_frames)

        return segments, labeled_frames

    def close(self) -> None:
        self.pose.close()

    # ---------- INTERNAL HELPERS ----------

    def _classify_frames(self, frames: List[FrameFeatures]) -> List[FrameFeatures]:
        ankle_vals = np.array(
            [f.ankle_y for f in frames if not np.isnan(f.ankle_y)]
        )

        if len(ankle_vals) == 0:
            for f in frames:
                f.phase = "unknown"
            return frames

        floor_y = float(np.nanmax(ankle_vals))

        for f in frames:
            ay, wy, hy = f.ankle_y, f.wrist_y, f.hip_y
            torso_angle = f.torso_angle
            hip_line_angle = f.hip_line_angle

            if any(np.isnan(v) for v in [ay, wy, hy, torso_angle, hip_line_angle]):
                phase = "unknown"
            else:
                feet_on_floor = ay > (floor_y - 0.03)
                hands_on_floor = wy > (floor_y - 0.03)
                feet_above_hips = ay < hy
                torso_vertical = torso_angle < 25.0
                body_straight = abs(hip_line_angle - 180.0) < 25.0

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

            f.phase = phase

        return frames

    def _group_segments(self, labeled_frames: List[FrameFeatures]) -> List[PhaseSegment]:
        if not labeled_frames:
            return []

        segments: List[PhaseSegment] = []
        current_phase = labeled_frames[0].phase or "unknown"
        start_idx = 0

        for i in range(1, len(labeled_frames)):
            phase = labeled_frames[i].phase
            if phase != current_phase:
                start_frame = labeled_frames[start_idx]
                end_frame = labeled_frames[i - 1]
                segments.append(
                    PhaseSegment(
                        phase=current_phase,
                        start_frame=start_frame.frame_idx,
                        end_frame=end_frame.frame_idx,
                        start_time=start_frame.time,
                        end_time=end_frame.time,
                    )
                )
                current_phase = phase or "unknown"
                start_idx = i

        start_frame = labeled_frames[start_idx]
        end_frame = labeled_frames[-1]
        segments.append(
            PhaseSegment(
                phase=current_phase,
                start_frame=start_frame.frame_idx,
                end_frame=end_frame.frame_idx,
                start_time=start_frame.time,
                end_time=end_frame.time,
            )
        )

        return segments
