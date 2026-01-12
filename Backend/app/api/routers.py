from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Path
from pydantic import BaseModel
from fastapi.responses import FileResponse
from pathlib import Path as PathLib
import uuid
import os
import time

from services.ProcessingPipelineService import ProcessingPipelineService

router = APIRouter()
processing_pipeline_service = ProcessingPipelineService()

# base paths relative to Backend/
BASE_DIR = PathLib(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / ".temp"

TEMP_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_files(path: PathLib):
    """
    Removes all files in a directory and then the directory itself.
    """
    for sub in path.iterdir():
        if sub.is_file():
            sub.unlink()
    path.rmdir()

@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks, 
    video: UploadFile = File(...)
):
    """
    Uploads a video of a gymnastics exercise.

    Args:
        background_tasks (BackgroundTasks): FastAPI background tasks manager.
        video (UploadFile): The video file to analyze.

    Returns:
        dict: {"status": "success", "pid": <process_id>}.
    """
    if not video.filename.lower().endswith( (".mp4", ".mov", ".avi", ".mkv") ):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    process_id = str(uuid.uuid4())
    process_dir = TEMP_DIR / process_id
    process_dir.mkdir()

    input_folder = process_dir / "input" 
    input_folder.mkdir()
    
    input_video_path = input_folder / video.filename

    with input_video_path.open("wb") as buffer:
        buffer.write(await video.read())

    background_tasks.add_task(time.sleep, 600)
    background_tasks.add_task(cleanup_files, process_dir)

    return {
        "status": "success",
        "pid": process_id
    }
    


class ProcessConfig(BaseModel):
    exercise_name: str
    
@router.post("/process/{process_id}")
async def process_video(
    process_config: ProcessConfig,
    process_id: str = Path(..., description="Process id, assigned upon /upload")
):
    """
    Processes video uploaded previously according to specified exercise.

    Args:
        process_config,
        process_id: Assigned upon /upload.

    Returns:
        dict: {"status": "success", "pid": <process_id>}.
    """
    
    process_dir = TEMP_DIR / process_id
    if not os.path.exists(process_dir):
        raise(HTTPException(status_code=400, detail=f"Process id [{process_id}] is incorrect or process is already cleared."))
    
    try:
        video_name = os.scandir(process_dir / "input")[0]
    except:
        raise(HTTPException(status_code=500, detail=f"Input video file does not exist."))
    
    if not video_name.endswith(".mp4", ".mov", ".avi", ".mkv"):
        raise(HTTPException(status_code=500, detail=f"Input video file is corrupted."))
    
    output_folder = process_dir / "output"
    output_folder.mkdir()
    
    no_ext_name = video_name.split('.')[0]
    input_video_path = process_dir / "input" / video_name
    output_video_path = process_dir / "output" / video_name
    output_json_path = process_dir / "output" / f"{no_ext_name}.json"
    output_pdf_path = process_dir / "output" / f"{no_ext_name}.pdf"
    
    exercise_name = process_config.model_dump().get(exercise_name, None)
    
    if not exercise_name:
        raise(HTTPException(status_code=500, detail=f"exercise_name was not found in payload."))
    
    try:
        processing_pipeline_service.analyze_video(input_video_path=input_video_path,
                                                  output_video_path=output_video_path,
                                                  output_json_path=output_json_path,
                                                  output_pdf_path=output_pdf_path,
                                                  exercise_name=exercise_name)
    except:
        raise(HTTPException(status_code=500, detail=f"Error in video processing pipeline."))
    
    return {
        "status": "success",
        "pid": process_id
    }
