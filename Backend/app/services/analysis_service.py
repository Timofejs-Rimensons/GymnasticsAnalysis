import os
from typing import Tuple, List

from app.services.handstand_phase_service import HandstandPhaseService
from app.repositories.segment_stats_repository import SegmentStatsRepository
from app.models.handstand_models import FrameFeatures, PhaseSegment


class AnalysisService:
    """
    High-level orchestration:
    - run analysis on a video
    - save per-segment stats to JSON
    - optionally create a visualized video
    """

    def __init__(self):
        self._phase_service = HandstandPhaseService()
        self._stats_repo = SegmentStatsRepository()

    def analyze_to_json(
        self,
        video_path: str,
        json_output_path: str,
    ) -> Tuple[List[PhaseSegment], List[FrameFeatures], str]:
        segments, frames = self._phase_service.analyze_video(video_path)
        self._stats_repo.write_segment_stats(segments, frames, json_output_path)
        return segments, frames, json_output_path

    def visualize(
        self,
        video_path: str,
        output_video_path: str,
    ) -> str:
        """
        Reuses the same HandstandPhaseService instance to draw phases
        on top of video frames and save to disk.
        """
        import cv2
        import mediapipe as mp

        segments, frames = self._phase_service.analyze_video(video_path)
        phase_per_frame = {f.frame_idx: (f.phase or "") for f in frames}

        mp_pose = mp.solutions.pose
        mp_drawing = mp.solutions.drawing_utils
        mp_styles = mp.solutions.drawing_styles

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._phase_service.pose.process(image_rgb)

            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_styles.get_default_pose_landmarks_style(),
                )

            phase = phase_per_frame.get(frame_idx, "")
            if phase:
                cv2.putText(
                    frame,
                    phase,
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )

            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()
        return output_video_path

    def close(self) -> None:
        self._phase_service.close()
