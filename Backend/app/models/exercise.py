from sqlalchemy import Column, Integer, String, Text
from database import Base
from sqlalchemy.orm import relationship

class Exercise(Base):
    __tablename__ = 'exercises'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Relationships
    features = relationship("ExerciseFeature", back_populates="exercise")
    analysis_jobs = relationship("AnalysisJob", back_populates="exercise")
