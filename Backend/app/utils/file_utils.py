from fastapi import UploadFile, HTTPException
from app.config import settings
import os
import shutil
from pathlib import Path

def validate_video_file(file: UploadFile):
    """"
    Validate uploaded video file
    - check file extension
    - check file size
    """

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
async def save_upload_file(file: UploadFile, destination: str) -> str:
    """
    Save uploaded file to destination directory
    
    Args:
        file: UploadFile object from FastAPI
        destination: Directory path to save the file
    
    Returns:
        Full path to the saved file
    """
    os.makedirs(destination, exist_ok=True)
    
    file_path = os.path.join(destination, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path