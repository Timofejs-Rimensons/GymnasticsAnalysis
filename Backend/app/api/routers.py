from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import os

from app.services.analysis_service import AnalysisService

router = APIRouter()
analysis_service = AnalysisService()

# base paths relative to Backend/
BASE_DIR = Path(__file__).resolve().parent.parent  # -> app/
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze")
async def analyze_handstand(video: UploadFile = File(...)):
    # 1) simple file-type validation
    if not video.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # 2) save uploaded file
    input_path = UPLOAD_DIR / video.filename
    with input_path.open("wb") as f:
        f.write(await video.read())

    # 3) run analysis + JSON export
    json_path = OUTPUT_DIR / f"{input_path.stem}_segments.json"

    segments, frames, saved_json = analysis_service.analyze_to_json(
        str(input_path), str(json_path)
    )

    return {
        "success": True,
        "message": "Analysis completed",
        "json_path": str(saved_json),          # local path on server
        "segments": [s.__dict__ for s in segments],
    }


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "Handstand Analyzer API"}
