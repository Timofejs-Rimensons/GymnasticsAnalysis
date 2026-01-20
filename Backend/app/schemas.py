from pydantic import BaseModel, field_serializer
import uuid
from datetime import datetime

class AnalysisJobBase(BaseModel):
    video_filename: str

class AnalysisJobCreate(AnalysisJobBase):
    pass

class AnalysisJob(AnalysisJobBase):
    id: uuid.UUID
    status: str
    results: dict | None = None
    exercise_id: int | None = None
    created_at: datetime
    updated_at: datetime
    uploaded_at: datetime | None = None
    processed_at: datetime | None = None

    class Config:
        from_attributes = True
    
    @field_serializer('created_at', 'updated_at', 'uploaded_at', 'processed_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.strftime('%Y-%m-%d %H:%M')

class StatusResponse(BaseModel):
    status: str
    progress: int | None = 0

# Authentication Schemas
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.strftime('%Y-%m-%d %H:%M')

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

