from dataclasses import dataclass
from typing import Optional


@dataclass
class FrameFeatures:
    frame_idx: int
    time: float
    wrist_y: float
    hip_y: float
    ankle_y: float
    torso_angle: float
    hip_line_angle: float
    phase: Optional[str] = None


@dataclass
class PhaseSegment:
    phase: str
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
