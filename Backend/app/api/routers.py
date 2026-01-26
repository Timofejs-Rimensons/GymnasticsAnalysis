from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Path, Header, Request
from pydantic import BaseModel
import json
from fastapi.responses import FileResponse
from pathlib import Path as PathLib
import uuid
import os
import time
import shutil
import bcrypt

from services.ProcessingPipelineService import ProcessingPipelineService
from database import get_database

router = APIRouter()
processing_pipeline_service = ProcessingPipelineService()

BASE_DIR = PathLib(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / ".temp"

TEMP_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_directory(path: PathLib):
    """
    Safely and recursively removes a directory.
    """
    if path.exists() and path.is_dir():
        shutil.rmtree(path)

def cleanup_inactive_directories(ttl_seconds: int = 300):
    """
    Scans the temp directory and removes inactive process folders.
    """
    now = time.time()
    if not TEMP_DIR.exists():
        return

    for process_dir in TEMP_DIR.iterdir():
        if not process_dir.is_dir():
            continue

        status_json_path = process_dir / "status.json"
        if not status_json_path.exists():
            if now - process_dir.stat().st_mtime > ttl_seconds:
                cleanup_directory(process_dir)
            continue

        try:
            with open(status_json_path, 'r') as f:
                status_data = json.load(f)

            status = status_data.get('status', 'unknown')
            if status == 'processing':
                continue

            last_accessed = status_data.get('last_accessed_at', 0)
            if now - last_accessed > ttl_seconds:
                cleanup_directory(process_dir)

        except (json.JSONDecodeError, FileNotFoundError):
            if now - process_dir.stat().st_mtime > ttl_seconds:
                cleanup_directory(process_dir)
            continue



@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    user_id: str = Header(None, alias="X-User-Id")
):
    """
    Uploads a video of a gymnastics exercise.
    Also triggers a cleanup of old, inactive directories.
    If user_id is provided, creates a database record for history tracking.
    """
    background_tasks.add_task(cleanup_inactive_directories)
    
    # Debug: Log the received user ID
    print(f"📤 Upload request received - User ID: {user_id}, File: {video.filename}")

    if not video.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    process_id = str(uuid.uuid4())
    process_dir = TEMP_DIR / process_id
    process_dir.mkdir(parents=True, exist_ok=True)
    
    status_json_path = process_dir / "status.json"

    input_folder = process_dir / "input"
    input_folder.mkdir(parents=True, exist_ok=True)
    
    input_video_path = input_folder / video.filename

    with input_video_path.open("wb") as buffer:
        buffer.write(await video.read())
         
    now = time.time()
    status_data = {
        "filename": video.filename,
        "status": "pending",
        "progress": 0,
        "created_at": now,
        "last_accessed_at": now
    }
    with open(status_json_path, 'w') as status_file:
        json.dump(status_data, status_file)

    # Create database record for history tracking
    # Even for anonymous users, we create a record with null user_id
    try:
        db = get_database()
        # Use a default exercise type that matches the schema
        exercise_type = "handstand"  # Default to handstand, will be updated during processing

        # Debug: Print what we're trying to create
        print(f"Creating analysis record: user_id={user_id or 'anonymous'}, analysis_id={process_id}, file_name={video.filename}")

        # For anonymous users, we'll need to handle the user_id being None
        # We'll create a placeholder or allow NULL in the database
        analysis = db.create_analysis(
            analysis_id=process_id,
            user_id=user_id if user_id else None,  # Allow None for anonymous uploads
            file_name=video.filename,
            exercise_type=exercise_type
        )
        print(f"✓ Successfully created analysis record: {analysis['id']}")
    except Exception as e:
        # Don't fail the upload if database operation fails, but log more details
        print(f"❌ Failed to create database record: {e}")
        import traceback
        traceback.print_exc()

    return {
        "status": "success",
        "pid": process_id,
        "user_id": user_id  # Return user_id for frontend tracking
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
    Updates the 'last_accessed_at' timestamp for the process directory.
    """
    process_dir = TEMP_DIR / process_id
    if not process_dir.exists():
        raise(HTTPException(status_code=400, detail=f"Process id [{process_id}] is incorrect or process is already cleared."))
    
    status_json_path = process_dir / "status.json"

    try:
        with open(status_json_path, 'r+') as f:
            status_data = json.load(f)
            status_data['last_accessed_at'] = time.time()
            f.seek(0)
            json.dump(status_data, f)
            f.truncate()
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    
    try:
        with open(status_json_path, 'r') as f:
            status_data = json.load(f)
    except:
        raise(HTTPException(status_code=400, detail=f"Process id [{process_id}] is incorrect or process is already cleared."))

    video_name = status_data["filename"]
    
    
    output_folder = process_dir / "output"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    no_ext_name = video_name.split('.')[0]
    input_video_path = process_dir / "input" / video_name
    output_video_path = process_dir / "output" / video_name
    output_json_path = process_dir / "output" / f"{no_ext_name}.json"
    output_pdf_path = process_dir / "output" / f"{no_ext_name}.pdf"
    
    exercise_name = process_config.model_dump().get("exercise_name", None)
    
    if not exercise_name:
        raise(HTTPException(status_code=500, detail=f"exercise_name was not found in payload."))
    
    try:
        with open(status_json_path, 'r+') as f:
            status_data = json.load(f)
            status_data['status'] = 'processing'
            status_data['last_accessed_at'] = time.time()
            f.seek(0)
            json.dump(status_data, f)
            f.truncate()

        # Update database with exercise type and status
        try:
            db = get_database()
            db.update_analysis_status(process_id, 'processing', 0.1, exercise_type=exercise_name)
        except Exception as e:
            print(f"Warning: Could not update database: {e}")

        processing_pipeline_service.analyze_video(input_video_path=input_video_path,
                                                    output_video_path=output_video_path,
                                                    output_json_path=output_json_path,
                                                    output_pdf_path=output_pdf_path,
                                                    exercise_name=exercise_name,
                                                    status_json_path=status_json_path,
                                                    analysis_id=process_id)
    except:
        with open(status_json_path, 'w') as status_file:
            try:
                with open(status_json_path, 'r') as f:
                    status_data = json.load(f)
            except:
                status_data = {}
            status_data['status'] = 'failed'
            status_data['progress'] = 0
            status_data['last_accessed_at'] = time.time()
            json.dump(status_data, status_file)
        raise(HTTPException(status_code=500, detail="Error during video processing."))
    
    try:
        with open(status_json_path, 'r+') as f:
            status_data = json.load(f)
            status_data['last_accessed_at'] = time.time()
            f.seek(0)
            json.dump(status_data, f)
            f.truncate()
    except (json.JSONDecodeError, FileNotFoundError):
        pass

    return {
        "status": "success",
        "pid": process_id
    }


@router.get("/status/{process_id}")
async def get_status(
    process_id: str = Path(..., description="Process id, assigned upon /upload")
):
    process_dir = TEMP_DIR / process_id
    status_json_path = process_dir / "status.json"
    
    try:
        with open(status_json_path, 'r') as f:
            status_data = json.load(f)
    except:
        raise(HTTPException(status_code=400, detail=f"Process id [{process_id}] is incorrect or process is already cleared."))
    
    return status_data
    
    
@router.get("/download/{type}/{process_id}")
async def download_output(
    type: str = Path(..., description="Type of file: video/json/pdf"),
    process_id: str = Path(..., description="Process id, assigned upon /upload")
):
    process_dir = TEMP_DIR / process_id
    if not process_dir.exists():
        raise HTTPException(status_code=400, detail=f"Process id [{process_id}] is incorrect or process is already cleared.")
    
    status_json_path = process_dir / "status.json"
    
    try:
        with open(status_json_path, 'r+') as f:
            status_data = json.load(f)
            status_data['last_accessed_at'] = time.time()
            f.seek(0)
            json.dump(status_data, f)
            f.truncate()
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    
    try:
        with open(status_json_path, 'r') as f:
            status_data = json.load(f)
    except:
        raise HTTPException(status_code=400, detail=f"Process id [{process_id}] is incorrect or process is already cleared.")
    
    video_name = status_data.get("filename")
    if not video_name:
        raise HTTPException(status_code=500, detail="Original video filename not found in status data.")
    
    no_ext_name = video_name.split('.')[0]
    output_dir = process_dir / "output"
    
    if type == 'json':
        output_path = output_dir / f"{no_ext_name}.json"
        if not output_path.exists():
            raise HTTPException(status_code=404, detail=f"JSON output for process {process_id} not found.")
        with open(output_path, 'r') as f:
            processed_data = json.load(f)
        return processed_data
     
    elif type == 'video':
        output_path = output_dir / video_name
        if not output_path.exists():
            raise HTTPException(status_code=404, detail=f"Video output for process {process_id} not found.")
        return FileResponse(output_path, media_type="video/mp4", filename=video_name)
     
    elif type == 'pdf':
        output_path = output_dir / f"{no_ext_name}.pdf"
        if not output_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF output for process {process_id} not found.")
        return FileResponse(output_path, media_type="application/pdf", filename=f"{no_ext_name}.pdf")
     
    else:
        raise HTTPException(status_code=400, detail=f"Type '{type}' is not supported. Use one of these: video/json/pdf.")


@router.get("/history")
async def get_history(user_id: str = Header(None, alias="X-User-Id")):
    """
    Get all analyses for the current user.
    """
    print(f"🔍 History endpoint called with user_id: {user_id}")

    if not user_id:
        print("❌ No user_id provided, returning empty array")
        return []

    try:
        db = get_database()
        history = db.get_user_analyses(user_id)

        print(f"📦 Found {len(history)} analyses for user {user_id}")

        result = []
        for item in history:
            analysis_data = {
                "id": str(item['id']),
                "fileName": item['file_name'],
                "exercise_type": item['exercise_type'],  # snake_case to match frontend
                "exerciseType": item['exercise_type'],    # ALSO add camelCase
                "created_at": item['created_at'].isoformat() if item.get('created_at') else None,
                "status": item['status'],
                "score": float(item['overall_score']) if item.get('overall_score') is not None else None,
                "maxScore": float(item['max_score']) if item.get('max_score') is not None else None
            }
            result.append(analysis_data)
            print(f"  - {item['file_name']}: {item['exercise_type']}, score={item.get('overall_score')}")

        return result
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = None


@router.post("/register")
async def register_user(register_request: RegisterRequest):
    """
    Register a new user
    """
    try:
        # Hash the password
        password_hash = bcrypt.hashpw(register_request.password.encode('utf-8'), bcrypt.gensalt())
        
        # Register user in database
        db = get_database()
        user = db.register_user(
            email=register_request.email,
            password_hash=password_hash.decode('utf-8'),
            name=register_request.name
        )
        
        return {
            "status": "success",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"]
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")