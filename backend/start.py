# backend/start.py
from __future__ import annotations
import os
import sys
import logging

import uvicorn


def _log(msg: str) -> None:
    logging.getLogger("uvicorn.error").info(msg)


def _diagnostics():
    import platform
    torch = None
    audiocraft = None
    try:
        import torch as _t  # type: ignore
        torch = _t
    except Exception:
        pass
    try:
        import audiocraft as _a  # type: ignore
        audiocraft = _a
    except Exception:
        pass

    cuda_available = bool(getattr(torch, "cuda", None) and torch.cuda.is_available()) if torch else False
    cuda_runtime = getattr(getattr(torch, "version", None), "cuda", None) if torch else None

    _log("=== Startup Diagnostics ===")
    _log(f"Python: {platform.python_version()} on {platform.platform()}")
    _log(f"USE_HEAVY={os.getenv('USE_HEAVY','0')} ALLOW_FALLBACK={os.getenv('ALLOW_FALLBACK','1')}")
    _log(f"Build tag: {os.getenv('BUILD_TAG')}  Image tag: {os.getenv('IMAGE_TAG')}  GIT_SHA: {os.getenv('GIT_SHA')}")
    _log(f"torch={getattr(torch,'__version__',None)}  audiocraft={getattr(audiocraft,'__version__',None)}  cuda_available={cuda_available}  cuda_runtime={cuda_runtime}")


if __name__ == "__main__":
    from backend import main as mainmod

    _diagnostics()

    use_heavy = os.getenv("USE_HEAVY", "0") == "1"
    allow_fallback = os.getenv("ALLOW_FALLBACK", "1") == "1"

    if use_heavy:
        try:
            from backend.services import heavy_audiogen as heavy
            heavy.load_model()  # one-time attempt
            if not heavy.is_ready():
                raise RuntimeError(heavy.last_heavy_error() or "heavy model not ready")
            _log("✅ Heavy model initialized")
        except Exception as e:  # noqa: BLE001
            _log(f"❌ Heavy initialization failed: {e}")
            try:
                mainmod.note_error(e)
            except Exception:
                pass
            if not allow_fallback:
                _log("FATAL: ALLOW_FALLBACK=0 and heavy init failed. Exiting.")
                sys.exit(1)
            else:
                _log("Continuing with fallback mode.")

    # Mark startup complete before serving health
    try:
        mainmod.set_startup_complete(True)
    except Exception:
        pass

    # Print route table once
    try:
        app = mainmod.create_app()
        lines = []
        for r in app.router.routes:
            methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
            path = getattr(r, "path", "")
            lines.append(f"{methods:7s} {path}")
        _log("Route table (preview):\n" + "\n".join(lines))
    except Exception:
        pass

    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
