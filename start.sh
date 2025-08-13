#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

pkill -f "uvicorn backend.main:app" 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ -d frontend ]; then
  pushd frontend >/dev/null
  npm ci || npm install
  npm run build
  popd >/dev/null
fi

export AUDIO_PROVIDER="${AUDIO_PROVIDER:-procedural}"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
