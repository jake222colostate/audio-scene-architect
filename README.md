# SoundForge.AI

FastAPI backend with an optional Vite + React frontend.

## Endpoints
- `GET /api/health` and `GET /health`
- `POST /api/generate-audio` → returns JSON with URL of generated file
- Generated files served under `/audio/*`
- SPA served from `/` when `frontend/dist` exists, otherwise a simple landing page
- Debug diagnostics at `/api/_debug/{env,routes,torch,model}`

## Development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Visit http://127.0.0.1:8000/docs for interactive API docs.

## Smoke tests
```bash
# Local
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
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

# Docker
docker build -t soundforge:lite .
docker run --rm -p 8000:8000 soundforge:lite &
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
curl -I http://127.0.0.1:8000/ | head -n1
```

## RunPod
- **Port**: 8000
- **Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info`
- **Env** (optional): `PUBLIC_BASE_URL=https://<POD_ID>-8000.proxy.runpod.net`

Test URLs:
- `/api/health`
- `/docs`
- `/`

## GPU runbook

Build & push GPU image:
```bash
docker build -f Dockerfile.gpu -t docker.io/<you>/audio-scene-architect:gpu .
docker push docker.io/<you>/audio-scene-architect:gpu
```

RunPod (GPU pod) env:
```
USE_HEAVY=1
ALLOW_FALLBACK=0
AUDIOGEN_MODEL=facebook/audiogen-medium
PUBLIC_BASE_URL=https://<POD_ID>-8000.proxy.runpod.net
```

Smoke checks:
- `GET /api/version` → "cuda_available" should be true with a device name and null "last_heavy_error".
- `POST /api/selftest` → `{ "ok": true, "len": ..., "sr": 22050 }`.
- `POST /api/generate-audio` with `{"prompt":"leaves crunching under footsteps while walking","duration":8}` → response includes `"generator":"heavy"`.

## Troubleshooting

Quick checks for the audio generation endpoint:

```bash
# Correct request (should 200)
curl -s -X POST http://127.0.0.1:8000/api/generate-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt":"leaves crunching under footsteps","duration":8}' | jq

# Bad request examples (should 422 with helpful detail):
curl -s -X POST http://127.0.0.1:8000/api/generate-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt":"", "duration": 10}' | jq

curl -s -X POST http://127.0.0.1:8000/api/generate-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt":"rain on car roof", "duration": ""}' | jq
```
