#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:8000}"
echo "[1] Health..." && (curl -fsS "$BASE/health" >/dev/null || curl -fsS "$BASE/api/health" >/dev/null)
echo "[2] Version..." && curl -fsS "$BASE/api/version" | tee /tmp/version.json >/dev/null
echo "[3] Generate..." && RESP=$(curl -fsS -H "Content-Type: application/json" -d '{"prompt":"leaves crunching under footsteps","duration":8}' "$BASE/api/generate-audio"); echo "$RESP"
echo "$RESP" | grep -q '"ok":true'
URL=$(echo "$RESP" | sed -n 's/.*"file_url":"\([^"]*\)".*/\1/p')
echo "[4] HEAD audio: $URL" && (curl -IfsS "$BASE$URL" >/dev/null || curl -IfsS "$URL" >/dev/null)
echo "✔ E2E passed."
