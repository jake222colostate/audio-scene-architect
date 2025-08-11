#!/usr/bin/env bash
set -euo pipefail
URL="${1:-http://localhost:8000/api/ready}"
for i in {1..60}; do
  if curl -fsS "$URL" >/dev/null; then
    echo "Ready"
    exit 0
  fi
  sleep 2
done
echo "Not ready in time" >&2
exit 1
