from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Path, Form
from sqlalchemy.orm import Session
import uuid
from pathlib import Path as PathLib
import shutil
from datetime import datetime

import schemas
from database import get_db
from repositories.analysis_job_repository import analysis_job_repo
from services.ProcessingPipelineService import ProcessingPipelineService
from auth import get_current_user
from models.user import User

router = APIRouter()
processing_pipeline_service = ProcessingPipelineService()

# Exercise mapping
EXERCISE_MAP = {
    "handstand": 1,
    "straddle_jump": 2,
    "straddle jump": 2
}

# A temporary directory for video uploads before processing.
# In a production environment, this should be a managed file store like S3.
TEMP_VIDEO_DIR = PathLib(__file__).resolve().parent.parent / ".temp_videos"
TEMP_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_temp_video_file(path: PathLib):
    """Safely removes a file."""
    if path.exists() and path.is_file():
        path.unlink()

@router.post("/upload", response_model=schemas.AnalysisJob)
async def upload_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    exercise_name: str = Form(default="handstand"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a video for analysis.
    This creates a new analysis job record in the database.
    The video is stored temporarily and will be deleted after processing.
    """
    if not video.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Get exercise ID from mapping
    exercise_id = EXERCISE_MAP.get(exercise_name.lower(), 1)
    
    # Create filename with exercise name, time, and date format: exercise_HH:MM_dd-mm (using dash instead of slash)
    today = datetime.now()
    time_str = today.strftime("%H:%M")
    date_str = today.strftime("%d-%m")
    file_ext = PathLib(video.filename).suffix
    new_filename = f"{exercise_name}_{time_str}_{date_str}{file_ext}"
    
    # Store video file temporarily with new filename
    video_id = str(uuid.uuid4())
    video_path = TEMP_VIDEO_DIR / f"{video_id}_{new_filename}"
    with video_path.open("wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # Read video blob for storage
    with open(video_path, 'rb') as f:
        video_blob = f.read()

    # Create job record in the database with user_id, exercise_id and video_blob
    job = analysis_job_repo.create_job(
        db, 
        video_filename=str(video_path),
        exercise_id=exercise_id,
        video_blob=video_blob,
        user_id=current_user.id
    )
    
    return job

@router.post("/process/{job_id}", response_model=schemas.AnalysisJob)
async def process_video(
    background_tasks: BackgroundTasks,
    job_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Starts the analysis process for a given job_id.
    """
    job = analysis_job_repo.get_job(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != 'uploaded':
        raise HTTPException(status_code=400, detail=f"Job has status '{job.status}' and cannot be processed.")

    analysis_job_repo.update_job_status(db, job_id=job_id, status='processing')

    # Define paths for output files
    video_path = PathLib(job.video_filename)
    output_dir = video_path.parent / "output" / str(job.id)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_json_path = output_dir / "results.json"
    
    # In a real system, these would be uploaded to a file store (e.g., S3)
    # and their URLs would be saved in the results.
    output_video_path = output_dir / video_path.name
    output_pdf_path = output_dir / f"{video_path.stem}.pdf"

    try:
        # The processing service needs to be adapted to not use a status file.
        # For now, we assume it runs and puts the result in output_json_path.
        # We will mock the behavior of the processing service for now.
        
        # Call the actual analysis function with MediaPipe
        processing_pipeline_service.analyze_video(
            input_video_path=str(video_path),
            output_video_path=str(output_video_path),
            output_pdf_path=str(output_pdf_path),
            output_json_path=str(output_json_path),
            exercise_name="handstand",
            status_json_path=str(output_dir / "status.json")
        )

        # Once processing is done, read results and update the job
        with open(output_json_path, 'r') as f:
            import json
            results_data = json.load(f)

        job = analysis_job_repo.update_job_results(db, job_id=job_id, results=results_data, status='completed')

    except Exception as e:
        analysis_job_repo.update_job_results(db, job_id=job_id, results={"error": str(e)}, status='failed')
        raise HTTPException(status_code=500, detail=f"Error during video processing: {e}")
    finally:
        # Clean up the temporary uploaded video file
        background_tasks.add_task(cleanup_temp_video_file, PathLib(job.video_filename))

    return job

@router.get("/status/{job_id}", response_model=schemas.StatusResponse)
async def get_status(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves the current status of an analysis job.
    """
    job = analysis_job_repo.get_job(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Progress can be added to the model and updated during processing
    return {"status": job.status, "progress": 0}


@router.get("/results/{job_id}", response_model=schemas.AnalysisJob)
async def get_results(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves the results of a completed analysis job.
    """
    job = analysis_job_repo.get_job(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != 'completed':
        raise HTTPException(status_code=400, detail=f"Job status is '{job.status}'. Results are not available.")
        
    return job

@router.get("/video/{job_id}")
async def get_processed_video(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Serves the processed video with skeleton visualization.
    """
    from fastapi.responses import FileResponse
    
    job = analysis_job_repo.get_job(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Construct path to processed video
    video_path = PathLib(job.video_filename)
    output_dir = video_path.parent / "output" / str(job.id)
    output_video_path = output_dir / video_path.name
    
    if not output_video_path.exists():
        raise HTTPException(status_code=404, detail="Processed video not found")
    
    return FileResponse(
        path=output_video_path,
        media_type="video/mp4",
        filename=f"processed_{video_path.name}"
    )

@router.get("/history", response_model=list[schemas.AnalysisJob])
async def get_user_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all analysis jobs for the current user, ordered by most recent first.
    """
    jobs = analysis_job_repo.get_user_jobs(db, user_id=current_user.id)
    return jobs

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies the API and database connectivity.
    """
    try:
        # Try to connect to the database
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}