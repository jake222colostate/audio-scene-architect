#!/bin/bash
set -e
docker build -t soundforge-ai .
docker run -d --name test-container -p 8000:8000 soundforge-ai
# give it a moment
sleep 3
# Try health; if it fails, print logs and exit 1
if ! curl -sf http://127.0.0.1:8000/api/health > /dev/null; then
  echo "Health failed. Container logs:"
  docker logs --timestamps test-container || true
  exit 1
fi
echo "Health OK"
docker logs --since=10s test-container | sed -n '1,200p'

