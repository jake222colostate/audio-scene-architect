#!/usr/bin/env bash
set -euo pipefail

# Local
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
PID=$!
echo "=== Testing health endpoints ==="
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then
    echo "Health OK on attempt $i"
    break
  fi
  echo "Health not ready yet (attempt $i); sleeping 1s"
  sleep 1
done
curl -fsS http://127.0.0.1:8000/api/health >/dev/null && echo
curl -s -X POST http://127.0.0.1:8000/api/generate-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt":"leaves crunching under footsteps","duration":5}'
kill $PID
wait $PID || true
deactivate

# Docker
docker build -t soundforge:lite .
CID=$(docker run -d -p 8000:8000 soundforge:lite)
echo "=== Testing health endpoints ==="
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then
    echo "Health OK on attempt $i"
    break
  fi
  echo "Health not ready yet (attempt $i); sleeping 1s"
  sleep 1
done
if ! curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then
  echo "Health failed after retries; dumping logs"
  docker logs --timestamps $CID | tail -n 400
  docker stop $CID >/dev/null
  exit 1
fi
echo "Health OK"
curl -I http://127.0.0.1:8000/ | head -n1
docker stop $CID >/dev/null
