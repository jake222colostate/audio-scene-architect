# syntax=docker/dockerfile:1.6

# ---- Frontend build (optional) ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
# Always copy the directory, even if it only has .gitkeep
COPY frontend/ ./
# If there's a package.json, then build; otherwise skip.
RUN if [ -f package.json ]; then npm ci && npm run build; else echo "No frontend package.json; skipping SPA build."; fi

# ---- Backend runtime ----
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# System deps for audio + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Backend code & deps
COPY backend /app/backend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy built SPA **only if it exists**
RUN mkdir -p /app/frontend/dist
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Optional: entrypoint with preflight (keeps logs if boot fails)
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health >/dev/null || exit 1

ENV UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000 UVICORN_LOG_LEVEL=info APP_MODULE=backend.main:app
ENTRYPOINT ["/app/docker/entrypoint.sh"]
