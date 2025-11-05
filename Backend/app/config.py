from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API settings
    API_TITLE: str = "Gymnastics Analysis API"
    API_VERSION: str = "1.0.0"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    # Analysis settings
    PASSING_SCORE: float = 70.0

    # File settings
    UPLOAD_DIR: str = "storage/uploads"
    OUTPUT_DIR: str = "storage/outputs"
    TEMP_DIR: str = "storage/temp"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100 MB
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".avi", ".mov"]

    # MediaPipe settings
    MEDIAPIPE_MODEL_COMPLEXITY: int = 1
    POSE_MODEL_COMPLEXITY: int = 1
    MIN_DETECTION_CONFIDENCE: float = 0.5
    MIN_TRACKING_CONFIDENCE: float = 0.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()