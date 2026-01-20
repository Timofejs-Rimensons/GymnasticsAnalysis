import uuid
from sqlalchemy import Column, String, JSON, DateTime, func, event, Integer, LargeBinary, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_mixin, relationship
from database import Base

@declarative_mixin
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AnalysisJob(Base, TimestampMixin):
    __tablename__ = 'analysis_jobs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_filename = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, index=True)
    results = Column(JSON)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=True, index=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    video_blob = Column(LargeBinary, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analysis_jobs")
    exercise = relationship("Exercise", back_populates="analysis_jobs")
    processed_files = relationship("ProcessedFile", back_populates="job")
    pose_scores = relationship("PoseScore", back_populates="job")
