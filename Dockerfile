# syntax=docker/dockerfile:1.6

############################
# Frontend build (Vite)
############################
FROM node:20-slim AS frontend
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
ARG FRONTEND_DIR=frontend
WORKDIR /app/frontend

# Show what we're copying (helps debug CI paths)
RUN echo ">>> Expecting frontend dir: ${FRONTEND_DIR}"
# Copy exactly that directory from the build context
COPY ${FRONTEND_DIR}/ /app/frontend/

# Fail early if we expected a real app but it's not here
RUN if [[ ! -f package.json ]]; then \
      echo "ERROR: ${FRONTEND_DIR}/package.json not found in build context. Check build context, path, or case." >&2; \
      ls -la /app/frontend; exit 42; \
    fi

RUN echo ">>> npm ci"; npm ci
RUN echo ">>> npm run build"; npm run build

############################
# Backend runtime
############################
FROM python:3.11-slim AS runtime
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN echo ">>> apt-get deps" && \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential libsndfile1 ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY backend /app/backend
RUN echo ">>> pip install reqs" && pip install --no-cache-dir -r /app/backend/requirements.txt

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

# Always copy built SPA from the builder stage (if the build failed, we never reach here)
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# entrypoint + healthcheck (keep yours)
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD sh -c 'curl -fsS http://127.0.0.1:8000/health >/dev/null || curl -fsS http://127.0.0.1:8000/api/health >/dev/null'
ENV UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000 UVICORN_LOG_LEVEL=info APP_MODULE=backend.main:app
ENTRYPOINT ["/app/docker/entrypoint.sh"]
