import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, LargeBinary, ForeignKey, func, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_mixin
from database import Base

@declarative_mixin
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Relationships
    analysis_jobs = relationship("AnalysisJob", back_populates="user")

class ExerciseFeature(Base):
    __tablename__ = 'exercise_features'
    id = Column(Integer, primary_key=True)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False, index=True)
    feature_name = Column(String(255), nullable=False)
    description = Column(Text)
    feature_type = Column(String(50), nullable=False)  # 'pose', 'alignment', 'position', etc.
    max_score = Column(Float, nullable=False, default=10.0)
    
    # Relationships
    exercise = relationship("Exercise", back_populates="features")
    pose_scores = relationship("PoseScore", back_populates="feature")

class ProcessedFile(Base):
    __tablename__ = 'processed_files'
    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey('analysis_jobs.id'), nullable=False, index=True)
    file_type = Column(String(50), nullable=False, index=True)  # 'video', 'pdf', 'json'
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("AnalysisJob", back_populates="processed_files")

class PoseScore(Base):
    __tablename__ = 'pose_scores'
    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey('analysis_jobs.id'), nullable=False, index=True)
    feature_id = Column(Integer, ForeignKey('exercise_features.id'), nullable=False, index=True)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    feedback = Column(Text)
    needs_improvement = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    job = relationship("AnalysisJob", back_populates="pose_scores")
    feature = relationship("ExerciseFeature", back_populates="pose_scores")
