#!/usr/bin/env bash
set -euo pipefail

export UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
export UVICORN_PORT="${UVICORN_PORT:-8000}"
export UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"
export APP_MODULE="${APP_MODULE:-backend.main:app}"
export STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-30}"   # seconds to wait for health
export STARTUP_SLEEP_ON_FAIL="${STARTUP_SLEEP_ON_FAIL:-120}"  # keep alive so CI can grab logs

echo "=== Environment snapshot ==="
echo "PYTHON:      $(python -V 2>&1 || true)"
echo "PIP:         $(pip -V 2>&1 || true)"
echo "APP_MODULE:  ${APP_MODULE}"
echo "USE_HEAVY:   ${USE_HEAVY:-}"
echo "ALLOW_FALLBACK: ${ALLOW_FALLBACK:-}"
echo "AUDIOGEN_MODEL: ${AUDIOGEN_MODEL:-facebook/audiogen-medium}"
echo "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-}"
echo "HF_HOME: ${HF_HOME:-}"
echo "TRANSFORMERS_CACHE: ${TRANSFORMERS_CACHE:-}"

echo "=== System deps ==="
which ffmpeg || true
which sndfile-* || true
ldconfig -p 2>/dev/null | grep -E 'sndfile|cuda' || true

echo "=== Python preflight ==="
python - <<'PY' || { echo "!!! Python preflight FAILED"; sleep "$STARTUP_SLEEP_ON_FAIL"; exit 1; }
import sys, importlib, os
print("sys.version:", sys.version)
mods = ["fastapi", "uvicorn", "numpy", "soundfile"]
for m in mods:
    try:
        importlib.import_module(m)
        print(f"ok: import {m}")
    except Exception as e:
        print(f"fail: import {m}: {e}")
        raise
# Torch/CUDA diag (optional on CPU images)
try:
    import torch
    print("torch:", torch.__version__, "cuda_available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("torch.cuda.version:", getattr(torch.version, "cuda", None))
        print("torch.cuda.device:", torch.cuda.get_device_name(0))
except Exception as e:
    print("torch diag error:", e)
PY

echo "=== App import & route table ==="
python - <<'PY' || { echo "!!! App import FAILED"; sleep "$STARTUP_SLEEP_ON_FAIL"; exit 1; }
import importlib
mod = importlib.import_module("backend.main")
app = getattr(mod, "app")
for r in app.router.routes:
    methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
    path = getattr(r, "path", "")
    print(f"{methods:7s} {path}")
PY

echo "=== Starting Uvicorn ${APP_MODULE} on ${UVICORN_HOST}:${UVICORN_PORT} ==="
# Start uvicorn in the foreground (so container stops if it dies)
python -m uvicorn "${APP_MODULE}" --host "${UVICORN_HOST}" --port "${UVICORN_PORT}" --log-level "${UVICORN_LOG_LEVEL}" &
UV_PID=$!

echo "=== Waiting for health endpoint ==="
deadline=$((SECONDS + STARTUP_TIMEOUT))
while (( SECONDS < deadline )); do
  if curl -fsS "http://127.0.0.1:${UVICORN_PORT}/api/health" >/dev/null; then
    echo "Health OK"; wait ${UV_PID}
    exit $?
  fi
  # Show last few log lines while waiting
  if ps -p ${UV_PID} >/dev/null 2>&1; then
    echo "(waiting) uvicorn running; retrying health..."
  else
    echo "!!! uvicorn exited early. Dumping last logs (if any)."
    # keep container alive so CI can read full logs
    sleep "$STARTUP_SLEEP_ON_FAIL"
    exit 1
  fi
  sleep 1
done

echo "!!! Health never became ready within ${STARTUP_TIMEOUT}s. Keeping container alive for logs."
# keep container alive for a while so logs can be collected
sleep "$STARTUP_SLEEP_ON_FAIL"
exit 1

