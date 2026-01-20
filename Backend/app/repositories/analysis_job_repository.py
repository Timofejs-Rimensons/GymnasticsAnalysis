from sqlalchemy.orm import Session
import uuid
from datetime import datetime
import schemas
from models.analysis_job import AnalysisJob

class AnalysisJobRepository:
    def get_job(self, db: Session, job_id: uuid.UUID):
        return db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()

    def get_user_jobs(self, db: Session, user_id: uuid.UUID):
        """Get all jobs for a user, ordered by most recent first"""
        return db.query(AnalysisJob).filter(AnalysisJob.user_id == user_id).order_by(AnalysisJob.created_at.desc()).all()

    def create_job(self, db: Session, video_filename: str, exercise_id: int = None, video_blob: bytes = None, user_id: uuid.UUID = None) -> AnalysisJob:
        db_job = AnalysisJob(
            video_filename=video_filename, 
            status='uploaded',
            exercise_id=exercise_id,
            video_blob=video_blob,
            user_id=user_id,
            uploaded_at=datetime.now()
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job

    def update_job_status(self, db: Session, job_id: uuid.UUID, status: str):
        db_job = self.get_job(db, job_id)
        if db_job:
            db_job.status = status
            db.commit()
            db.refresh(db_job)
        return db_job

    def update_job_results(self, db: Session, job_id: uuid.UUID, results: dict, status: str):
        db_job = self.get_job(db, job_id)
        if db_job:
            db_job.results = results
            db_job.status = status
            db_job.processed_at = datetime.now()
            db.commit()
            db.refresh(db_job)
        return db_job

analysis_job_repo = AnalysisJobRepository()
