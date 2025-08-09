# ---- Frontend build (kept as-is if you already have it) ----
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

# System deps for audio + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Copy backend and install deps
COPY backend /app/backend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy built SPA if present
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Add entrypoint
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health >/dev/null || exit 1

ENV UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000 UVICORN_LOG_LEVEL=info APP_MODULE=backend.main:app
ENTRYPOINT ["/app/docker/entrypoint.sh"]
