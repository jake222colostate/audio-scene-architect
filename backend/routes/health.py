# backend/routes/health.py
from fastapi import APIRouter

router = APIRouter()


def _payload():
    return {"status": "ok"}


@router.get("/health", tags=["health"])
def health():
    return _payload()
