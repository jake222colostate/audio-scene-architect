# ---- Frontend build (optional) ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./ 2>/dev/null || true
RUN [ -f package.json ] && npm ci || true
COPY frontend ./ 2>/dev/null || true
RUN [ -f package.json ] && npm run build || true

# ---- Backend runtime ----
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# copy backend & install deps
COPY backend /app/backend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# copy frontend build if present
COPY --from=frontend /app/frontend/dist /app/frontend/dist

EXPOSE 8000

# Health probe—canonical path
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health >/dev/null || exit 1

# Run the CORRECT app module
CMD ["python","-m","uvicorn","backend.main:app","--host","0.0.0.0","--port","8000","--log-level","info"]
