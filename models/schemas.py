"""Pydantic models and schemas."""
from pydantic import BaseModel

class GenerateAudioRequest(BaseModel):
    prompt: str
    duration: int = 30

class JobStatus(BaseModel):
    status: str
    progress: int = 0
    message: str = ""