# syntax=docker/dockerfile:1.6
# ---- Frontend build (optional) ----
FROM node:20-slim AS frontend
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
WORKDIR /app/frontend
COPY frontend/ ./ || true
RUN if [[ -f package.json ]]; then \
      echo ">>> [frontend] npm ci"; npm ci; \
      echo ">>> [frontend] npm run build"; npm run build; \
    else \
      echo ">>> [frontend] No package.json; skipping build"; \
    fi

# ---- Backend runtime ----
FROM python:3.11-slim AS runtime
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# System deps
RUN echo ">>> [runtime] apt-get install deps" && \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential libsndfile1 ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Backend code & deps
COPY backend /app/backend
RUN echo ">>> [runtime] pip install (requirements.txt)" && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Build-time Python sanity checks (CPU image)
RUN echo ">>> [runtime] Python sanity checks" && python - <<'PY'
import sys, importlib
print("python:", sys.version)
for m in ["fastapi","uvicorn","numpy","soundfile"]:
    try:
        importlib.import_module(m)
        print("ok import:", m)
    except Exception as e:
        print("FAIL import:", m, "->", e); raise
PY

# Copy SPA if built
RUN mkdir -p /app/frontend/dist
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Entrypoint
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health >/dev/null || exit 1

ENV UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000 UVICORN_LOG_LEVEL=info APP_MODULE=backend.main:app
ENTRYPOINT ["/app/docker/entrypoint.sh"]
