# ---- Frontend build (if present) ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN [ -f package.json ] && npm ci || true
COPY frontend ./
RUN [ -f package.json ] && npm run build || true
RUN mkdir -p dist

# ---- Backend runtime ----
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

COPY backend /app/backend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy built SPA if it exists
COPY --from=frontend /app/frontend/dist /app/frontend/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health >/dev/null || exit 1

CMD ["python","-m","uvicorn","backend.main:app","--host","0.0.0.0","--port","8000","--log-level","info"]
