import os
from fastapi import APIRouter

router = APIRouter()
BUILD_TAG = os.getenv("BUILD_TAG", "dev")

@router.get("/health", tags=["meta"])
def health():
    return {"ok": True, "build": BUILD_TAG}
