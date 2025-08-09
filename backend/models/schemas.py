from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union


class GenerateAudioRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    duration: Union[int, str] = Field(
        ..., description="Seconds, 1–30 heavy, 1–120 fallback"
    )
    seed: Optional[Union[int, str]] = None
    sample_rate: Optional[Union[int, str]] = 44100

    @field_validator("prompt")
    @classmethod
    def _strip_prompt(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Prompt cannot be empty")
        return v

    @field_validator("duration")
    @classmethod
    def _coerce_duration(cls, v):
        try:
            iv = int(v)
        except Exception:
            raise ValueError("Duration must be an integer")
        if not (1 <= iv <= 120):
            raise ValueError("Duration must be between 1 and 120 seconds")
        return iv

    @field_validator("sample_rate")
    @classmethod
    def _coerce_sr(cls, v):
        try:
            iv = int(v)
        except Exception:
            raise ValueError("sample_rate must be an integer")
        if not (8000 <= iv <= 48000):
            raise ValueError("sample_rate must be 8000–48000")
        return iv

    @field_validator("seed")
    @classmethod
    def _coerce_seed(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except Exception:
            raise ValueError("seed must be an integer if provided")

