from pydantic import BaseModel, Field, validator

class GenerateAudioRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=500)
    duration: int = Field(..., ge=1, le=120)

    @validator("prompt")
    def strip_prompt(cls, v):
        return v.strip()
