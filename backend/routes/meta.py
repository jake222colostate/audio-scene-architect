from fastapi import APIRouter, Request
from backend.utils.diagnostics import gather_version_payload

router = APIRouter()

@router.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}

@router.get("/version", tags=["meta"])
def version(request: Request):
    return gather_version_payload(request.app)
