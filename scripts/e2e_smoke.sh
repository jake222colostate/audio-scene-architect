#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:8000}"

echo "[1] Health checks..."
curl -fsS "$BASE/health" >/dev/null || curl -fsS "$BASE/api/health" >/dev/null

echo "[2] Version..."
curl -fsS "$BASE/api/version" | tee /tmp/version.json

echo "[3] Generate short audio..."
REQ='{"prompt":"leaves crunching under footsteps","duration":8}'
RESP=$(curl -fsS -H "Content-Type: application/json" -d "$REQ" "$BASE/api/generate-audio")
echo "$RESP" | tee /tmp/gen.json

OK=$(echo "$RESP" | sed -n 's/.*"ok":\s*\(true\|false\).*/\1/p')
URL=$(echo "$RESP" | sed -n 's/.*"file_url":\s*"\([^"]*\)".*/\1/p')

if [ "$OK" != "true" ]; then
  echo "Generation failed"; exit 1
fi

echo "[4] HEAD audio..."
curl -IfsS "$BASE$URL" >/dev/null || curl -IfsS "$URL" >/dev/null

echo "✔ E2E passed."
