#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://127.0.0.1:8000}

echo "== Health =="
curl -sf "$BASE_URL/health" && echo
curl -sf "$BASE_URL/api/health" && echo

echo "== Version (key fields) =="
curl -sf "$BASE_URL/api/version" | jq '{build, platform, cuda, heavy, frontend}'

echo "== Generate (8s) =="
RES=$(curl -s -X POST "$BASE_URL/api/generate-audio" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"leaves crunching under footsteps","duration":8}')
echo "$RES" | jq .
OK=$(echo "$RES" | jq -r .ok)
URL=$(echo "$RES" | jq -r .file_url)
if [ "$OK" != "true" ] || [ -z "$URL" ] || [ "$URL" = "null" ]; then
  echo "❌ generate-audio failed or missing file_url"; exit 1; fi

echo "== HEAD generated file =="
curl -If "$BASE_URL$URL" | head -n 1 | grep -q "200" && echo "✅ File reachable"
