from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import os
import time

from app.services.ProcessingPipelineService import ProcessingPipelineService

router = APIRouter()
processing_pipeline_service = ProcessingPipelineService()

# base paths relative to Backend/
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "temp"

DATA_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_files(path: Path):
    """
    Removes all files in a directory and then the directory itself.
    """
    for sub in path.iterdir():
        if sub.is_file():
            sub.unlink()
    path.rmdir()

@router.post("/analyze")
async def analyze_video_endpoint(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    exercise_name: str = Form(...)
):
    """
    Analyzes a video of a gymnastics exercise.

    Args:
        background_tasks (BackgroundTasks): FastAPI background tasks manager.
        video (UploadFile): The video file to analyze.
        exercise_name (str): The name of the exercise in the video.

    Returns:
        dict: A dictionary containing the URLs to the analysis results.
    """
    if not video.filename.lower().endswith( (".mp4", ".mov", ".avi", ".mkv") ):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    request_id = str(uuid.uuid4())
    request_dir = DATA_DIR / request_id
    request_dir.mkdir()

    input_video_path = request_dir / video.filename
    output_video_path = request_dir / f"{input_video_path.stem}_output.mp4"
    output_json_path = request_dir / f"{input_video_path.stem}_output.json"
    output_pdf_path = request_dir / f"{input_video_path.stem}_output.pdf"

    with input_video_path.open("wb") as buffer:
        buffer.write(await video.read())

    try:
        processing_pipeline_service.analyze_video(
            str(input_video_path),
            str(output_video_path),
            str(output_pdf_path),
            str(output_json_path),
            exercise_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during analysis: {e}")

    background_tasks.add_task(time.sleep, 60)
    background_tasks.add_task(cleanup_files, request_dir)

    return {
        "success": True,
        "message": "Analysis completed",
        "request_id": request_id,
        "results": {
            "video": f"/output/{request_id}/{output_video_path.name}",
            "json": f"/output/{request_id}/{output_json_path.name}",
            "pdf": f"/output/{request_id}/{output_pdf_path.name}",
        },
    }

@router.get("/output/{request_id}/{filename}")
async def get_output_file(request_id: str, filename: str):
    """
    Retrieves an output file from a specific analysis request.

    Args:
        request_id (str): The ID of the analysis request.
        filename (str): The name of the file to retrieve.

    Returns:
        FileResponse: The requested file.
    """
    file_path = DATA_DIR / request_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path))