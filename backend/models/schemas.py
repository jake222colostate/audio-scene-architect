from pydantic import BaseModel, Field
from typing import Optional


class GenerateAudioRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    duration: int = Field(..., ge=1, le=30)  # heavy path practical cap
    seed: Optional[int] = None
    sample_rate: int = Field(default=44100, ge=8000, le=48000)
