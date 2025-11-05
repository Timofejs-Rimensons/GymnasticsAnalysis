from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import AnalysisResponse
from app.services.video_processor import VideoProcessor
from app.services.phase_analyzer import PhaseAnalyzer
from app.services.export_service import ExportService
from app.utils.file_utils import save_upload_file, validate_video_file
from app.config import settings
import os

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_handstand(video: UploadFile = File(...)):
    """
    Upload a handstand video and get analysis results with grading for 5 phases:
    1. Starting Position
    2. Upswing
    3. Hand Placement
    4. Body Position
    5. Landing & Finishing
    """
    try:
        # Validate file
        validate_video_file(video)
        
        # Save uploaded file
        video_path = await save_upload_file(video, settings.UPLOAD_DIR)
        
        # Process video with MediaPipe
        print(f"Processing video: {video_path}")
        processor = VideoProcessor()
        landmarks_data = processor.process_video(video_path)
        
        if not landmarks_data:
            raise HTTPException(status_code=400, detail="No pose detected in video")
        
        print(f"Detected {len(landmarks_data)} frames with pose landmarks")
        
        # Analyze phases
        analyzer = PhaseAnalyzer()
        analysis_result = analyzer.analyze(landmarks_data, video.filename)
        
        print(f"Analysis complete - Score: {analysis_result.overall_score}")
        
        # Generate exports
        exporter = ExportService()
        csv_path = exporter.generate_csv(analysis_result)
        pdf_path = exporter.generate_pdf(analysis_result)
        
        # Create URLs for downloads
        csv_url = f"http://localhost:8000/outputs/{os.path.basename(csv_path)}"
        pdf_url = f"http://localhost:8000/outputs/{os.path.basename(pdf_path)}"
        
        return AnalysisResponse(
            success=True,
            message="Analysis completed successfully",
            result=analysis_result,
            csv_url=csv_url,
            pdf_url=pdf_url
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Handstand Analyzer API"
    }