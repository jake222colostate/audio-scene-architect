#!/usr/bin/env bash
set -euo pipefail

export UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
export UVICORN_PORT="${UVICORN_PORT:-8000}"
export UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"
export APP_MODULE="${APP_MODULE:-backend.main:app}"

echo "=== Preflight: checking filesystem ==="
ls -lah /app || true
ls -lah /app/backend || true
python - <<'PY' || {
  echo "=== Python preflight FAILED. See traceback above. ==="
  # keep container alive a bit so CI/RunPod can read logs
  sleep 60
  exit 1
}
import sys, pkgutil, importlib
print("Python:", sys.version)
print("Trying to import FastAPI/Uvicorn…")
import fastapi, uvicorn  # noqa
print("Importing APP_MODULE…")
mod_name, app_name = "backend.main", "app"
try:
    module = importlib.import_module(mod_name)
    app = getattr(module, app_name)
    print("APP_MODULE import OK:", module, app)
except Exception as e:
    print("APP_MODULE import error:", e)
    raise
print("Listing routes…")
for r in app.router.routes:
    methods = ",".join(sorted(getattr(r,"methods",["GET"])))
    path = getattr(r, "path", "")
    print(f"  {methods:7s} {path}")
PY

echo "=== Starting Uvicorn ${APP_MODULE} on ${UVICORN_HOST}:${UVICORN_PORT} ==="
exec python -m uvicorn "${APP_MODULE}" --host "${UVICORN_HOST}" --port "${UVICORN_PORT}" --log-level "${UVICORN_LOG_LEVEL}"
