#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://127.0.0.1:8000}

curl -sf "${BASE_URL}/api/health" | jq -e '.status == "ok"' >/dev/null

VER=$(curl -sf "${BASE_URL}/api/version")
echo "$VER" | jq . >/dev/null

# Required keys
for key in build_tag use_heavy allow_fallback libs last_error; do
  echo "$VER" | jq -e ".${key}" >/dev/null
done

USE_HEAVY=$(echo "$VER" | jq -r .use_heavy)
CUDA=$(echo "$VER" | jq -r .cuda.cuda_available)
AUDIOCRAFT=$(echo "$VER" | jq -r .libs.audiocraft)

if [[ "$USE_HEAVY" == "1" && "$CUDA" == "true" ]]; then
  if [[ "$AUDIOCRAFT" == "null" || -z "$AUDIOCRAFT" ]]; then
    echo "Expected audiocraft lib present in GPU build" >&2
    exit 1
  fi
fi

# Optional short generation in fallback mode
curl -sf -X POST "${BASE_URL}/api/generate-audio" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"crisp leaves under shoes","duration":2}' | jq -e '.ok == true' >/dev/null

# HEAD the produced file if url is present
URL=$(curl -sf -X POST "${BASE_URL}/api/generate-audio" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"soft wind","duration":1}' | jq -r .file_url)
if [[ -n "$URL" && "$URL" != "null" ]]; then
  curl -If "${BASE_URL}${URL}" | head -n1 | grep -q "200"
fi

echo "✅ Acceptance checks passed"
