# backend/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class GenerateAudioRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    duration: int = Field(..., ge=1, le=120)
    sample_rate: Optional[int] = Field(None, ge=8000, le=48000)
