#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:8000}"

echo "[1] Health..."
curl -fsS "$BASE/health" >/dev/null || curl -fsS "$BASE/api/health" >/dev/null

echo "[2] Version..."
curl -fsS "$BASE/api/version" | tee /tmp/version.json

echo "[3] Generate short audio..."
REQ='{"prompt":"leaves crunching under footsteps","duration":8}'
RESP=$(curl -fsS -H "Content-Type: application/json" -d "$REQ" "$BASE/api/generate-audio")
echo "$RESP" | tee /tmp/gen.json

if ! echo "$RESP" | grep -q '"ok": true'; then
  echo "Generation failed"; exit 1
fi

URL=$(echo "$RESP" | sed -n 's/.*"file_url":"\([^"]*\)".*/\1/p')
echo "[4] HEAD audio: $URL"
curl -IfsS "$BASE$URL" >/dev/null || curl -IfsS "$URL" >/dev/null

echo "✔ E2E passed."
