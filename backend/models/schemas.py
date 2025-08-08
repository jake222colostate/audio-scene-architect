from pydantic import BaseModel, Field

class GenerateAudioRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    duration: int = Field(..., ge=1, le=120)
