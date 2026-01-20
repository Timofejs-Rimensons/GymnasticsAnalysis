from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class AnalyticalModel(Base):
    __tablename__ = 'analytical_models'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    model_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    exercise = relationship("Exercise")
