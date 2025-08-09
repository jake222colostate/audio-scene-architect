#!/usr/bin/env bash
set -euo pipefail

export UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
export UVICORN_PORT="${UVICORN_PORT:-8000}"
export UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"
export APP_MODULE="${APP_MODULE:-backend.main:app}"

echo "=== Preflight: import app & list routes ==="
python - <<'PY' || { echo "Preflight FAILED"; sleep 60; exit 1; }
import importlib
mod = importlib.import_module("backend.main")
app = getattr(mod, "app")
for r in app.router.routes:
    methods = ",".join(sorted(getattr(r,"methods",["GET"])))
    path = getattr(r,"path","")
    print(f"{methods:7s} {path}")
PY

echo "=== Starting Uvicorn ${APP_MODULE} on ${UVICORN_HOST}:${UVICORN_PORT} ==="
exec python -m uvicorn "${APP_MODULE}" --host "${UVICORN_HOST}" --port "${UVICORN_PORT}" --log-level "${UVICORN_LOG_LEVEL}"
