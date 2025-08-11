"""Health check and diagnostic routes."""
from fastapi import APIRouter
from utils.system import check_system_health

router = APIRouter(prefix="/api")

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/ping")
async def ping():
    return {"status": "alive", "port": 8000}

@router.get("/diagnostic")
async def diagnostic_endpoint():
    """System health check endpoint for monitoring and debugging."""
    healthy, message = check_system_health()
    
    return {
        "status": "healthy" if healthy else "unhealthy", 
        "message": message,
        "service": "SoundForge.AI Backend"
    }

@router.get("/self-test")
def self_test():
    from services.audio_generation import _generate_procedural_ambience
    from config import OUTPUT_DIR
    import uuid, os
    filename = f"{uuid.uuid4().hex}.mp3"
    seg = _generate_procedural_ambience("test", 10)
    out = os.path.join(OUTPUT_DIR, filename)
    seg.export(out, format="mp3")
    return {"status":"ok","filename":filename,"file_url":f"/audio/{filename}"}
