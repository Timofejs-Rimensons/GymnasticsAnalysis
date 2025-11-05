from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class PhaseType(str, Enum):
    STARTING_POSITION = "starting_position"
    UPSWING = "upswing"
    HAND_PLACEMENT = "hand_placement"
    BODY_POSITION = "body_position"
    LANDING_FINISHING = "landing_finishing"

class PhaseGrade(BaseModel):
    phase: PhaseType
    phase_name: str
    score: float  # 0-100
    is_correct: bool  # True if passed (>=70), False if error (<70)
    feedback: str
    key_metrics: Dict[str, float]  # e.g., {"shoulder_angle": 175, "hip_angle": 180}
    frame_range: tuple[int, int]
    error_details: List[str] = []

class AnalysisResult(BaseModel):
    video_filename: str
    overall_score: float
    total_correct_phases: int
    total_error_phases: int
    phases: List[PhaseGrade]
    total_frames: int
    duration_seconds: float
    csv_path: Optional[str] = None
    pdf_path: Optional[str] = None

class AnalysisResponse(BaseModel):
    success: bool
    message: str
    result: Optional[AnalysisResult] = None
    csv_url: Optional[str] = None
    pdf_url: Optional[str] = None