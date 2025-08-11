#!/usr/bin/env bash
set -euo pipefail

export UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
export UVICORN_PORT="${UVICORN_PORT:-8000}"
export UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"
export APP_MODULE="${APP_MODULE:-backend.main:app}"
export STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-40}"
export STARTUP_SLEEP_ON_FAIL="${STARTUP_SLEEP_ON_FAIL:-120}"

echo "=== ENV SNAPSHOT ==="
env | sort | sed -n '1,120p' || true
echo "=== PYTHON SNAPSHOT ==="
python -V || true
pip -V || true

echo "=== PRE-FLIGHT IMPORTS ==="
python - <<'PY' || { echo "!!! Preflight imports FAILED"; sleep "$STARTUP_SLEEP_ON_FAIL"; exit 1; }
import sys, importlib
mods = ["fastapi","uvicorn","numpy","soundfile"]
for m in mods:
    try:
        importlib.import_module(m); print("ok import:", m)
    except Exception as e:
        print("FAIL import:", m, "->", e); raise
try:
    import torch
    print("torch:", torch.__version__, "cuda_available:", torch.cuda.is_available(), "cuda:", getattr(torch.version, "cuda", None))
    if torch.cuda.is_available():
        print("cuda device:", torch.cuda.get_device_name(0))
except Exception as e:
    print("torch diag error:", e)
PY

echo "=== APP IMPORT & ROUTES ==="
python - <<'PY' || { echo "!!! App import FAILED"; sleep "$STARTUP_SLEEP_ON_FAIL"; exit 1; }
import importlib
mod = importlib.import_module("backend.main")
app = getattr(mod, "app")
for r in app.router.routes:
    methods=",".join(sorted(getattr(r,"methods",["GET"])))
    print(f"{methods:7s} {getattr(r,'path','')}")
PY

echo "=== START UVICORN ==="
python -m uvicorn "${APP_MODULE}" --host "${UVICORN_HOST}" --port "${UVICORN_PORT}" --log-level "${UVICORN_LOG_LEVEL}" &
UV_PID=$!

echo "=== WAIT FOR /api/health (${STARTUP_TIMEOUT}s) ==="
deadline=$((SECONDS + STARTUP_TIMEOUT))
while (( SECONDS < deadline )); do
  if curl -fsS "http://127.0.0.1:${UVICORN_PORT}/api/health" >/dev/null; then
    echo "Health OK"; wait ${UV_PID}; exit $?
  fi
  if ! ps -p ${UV_PID} >/dev/null 2>&1; then
    echo "!!! uvicorn exited early — leaving container alive for logs"
    sleep "$STARTUP_SLEEP_ON_FAIL"; exit 1
  fi
  echo "(waiting) health not ready; retrying…"
  sleep 1
done
echo "!!! health not ready in time — keeping container alive for logs"
sleep "$STARTUP_SLEEP_ON_FAIL"; exit 1
