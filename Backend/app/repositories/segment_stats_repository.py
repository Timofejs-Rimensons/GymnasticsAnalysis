import json
from typing import List, Dict

import numpy as np

from app.models.handstand_models import FrameFeatures, PhaseSegment


class SegmentStatsRepository:
    """
    Computes and writes per-segment height/angle stats to JSON.
    """

    def __init__(self, json_indent: int = 2):
        self.json_indent = json_indent

    def write_segment_stats(
        self,
        segments: List[PhaseSegment],
        frames: List[FrameFeatures],
        json_path: str,
    ) -> None:
        # map frame_idx -> FrameFeatures
        frame_lookup: Dict[int, FrameFeatures] = {f.frame_idx: f for f in frames}

        payload = []

        for seg in segments:
            seg_frames: List[FrameFeatures] = [
                frame_lookup[i]
                for i in range(seg.start_frame, seg.end_frame + 1)
                if i in frame_lookup
            ]

            def clean_array(values):
                arr = np.array(
                    [v for v in values if not np.isnan(v)], dtype=float
                )
                if arr.size == 0:
                    return {
                        "min": None,
                        "max": None,
                        "mean": None,
                    }
                return {
                    "min": float(arr.min()),
                    "max": float(arr.max()),
                    "mean": float(arr.mean()),
                }

            wrist_stats = clean_array([f.wrist_y for f in seg_frames])
            hip_stats = clean_array([f.hip_y for f in seg_frames])
            ankle_stats = clean_array([f.ankle_y for f in seg_frames])
            torso_stats = clean_array([f.torso_angle for f in seg_frames])
            hipline_stats = clean_array([f.hip_line_angle for f in seg_frames])

            payload.append(
                {
                    "phase": seg.phase,
                    "start_frame": seg.start_frame,
                    "end_frame": seg.end_frame,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "heights": {
                        "wrist_y": wrist_stats,
                        "hip_y": hip_stats,
                        "ankle_y": ankle_stats,
                    },
                    "angles": {
                        "torso_angle": torso_stats,
                        "hip_line_angle": hipline_stats,
                    },
                }
            )

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=self.json_indent)

        print(f"[JSON] Segment stats saved to {json_path}")
