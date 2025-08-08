from fastapi import APIRouter

router = APIRouter()

# Canonical health payload
def _payload():
    return {"status": "ok"}

# These become /health when included without prefix
@router.get("/health")
def health_alias():
    return _payload()

# These become /api/health when included with prefix="/api"
@router.get("/health", tags=["health"]) 
def health_canonical():
    return _payload()
