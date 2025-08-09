from __future__ import annotations

import time
from fastapi import APIRouter, Request
from backend.utils.diagnostics import gather_version_payload

router = APIRouter()


@router.get("/debug/routes", tags=["debug"])
def debug_routes(request: Request):
    items = []
    for r in request.app.router.routes:
        methods = sorted(getattr(r, "methods", ["GET"]))
        items.append({"path": getattr(r, "path", ""), "methods": methods})
    return items


@router.get("/debug/state", tags=["debug"])
def debug_state(request: Request):
    payload = gather_version_payload(request.app)
    payload["heavy_logs"] = getattr(request.app.state, "heavy_logs", [])
    return payload


@router.post("/debug/selftest", tags=["debug"])
def debug_selftest(request: Request):
    t0 = time.time()
    ok = True
    err = None
    try:
        from backend.services import heavy_audiogen
        heavy_audiogen.generate("test tone", 2)
    except Exception as e:
        ok = False
        err = str(e)
    elapsed = int((time.time() - t0) * 1000)
    return {"ok": ok, "ms": elapsed, "error": err}
