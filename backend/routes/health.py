from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/health")
def health_root_alias():
    return {"status": "ok"}

# canonical (also available when included with /api prefix)
@router.get("/api/health")
def health_canonical():
    return {"status": "ok"}
