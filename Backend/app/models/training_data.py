from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    source_description = Column(String(255))
    scores = Column(JSON, nullable=False)

    exercise = relationship("Exercise")
