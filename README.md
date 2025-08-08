# SoundForge.AI

FastAPI backend with an optional Vite + React frontend.

## Endpoints
- `GET /api/health` and `GET /health`
- `POST /api/generate-audio` → returns JSON with URL of generated file
- Generated files served under `/audio/*`
- SPA served from `/` when `frontend/dist` exists, otherwise a simple landing page

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
sleep 2
curl -sf http://127.0.0.1:8000/api/health && echo
curl -s -X POST http://127.0.0.1:8000/api/generate-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt":"leaves crunching under footsteps","duration":5}'

# Docker
docker build -t soundforge:lite .
docker run --rm -p 8000:8000 soundforge:lite &
sleep 3
curl -sf http://127.0.0.1:8000/api/health && echo
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
