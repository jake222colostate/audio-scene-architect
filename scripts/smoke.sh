#!/usr/bin/env bash
set -euo pipefail

echo "== Health =="
curl -sf http://127.0.0.1:8000/api/health && echo
curl -sf http://127.0.0.1:8000/health && echo

echo "== Generate =="
curl -s -X POST http://127.0.0.1:8000/api/generate-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt":"leaves crunching under footsteps","duration":5}' | jq .
