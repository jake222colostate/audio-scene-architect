# ---- Frontend build (root SPA) ----
FROM node:20-slim AS frontend
WORKDIR /app

# Install deps (ci if lock exists)
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy source and build
COPY . .
RUN npm run build

# Place build at /app/frontend/dist and write build-info
RUN mkdir -p /app/frontend && \
    mv dist /app/frontend/dist && \
    node -v > /tmp/nodev && npm -v > /tmp/npmv && \
    node -e "const fs=require('fs');const p='/app/frontend/dist/build-info.json';const info={node:fs.readFileSync('/tmp/nodev','utf8').trim(),npm:fs.readFileSync('/tmp/npmv','utf8').trim(),built_at:new Date().toISOString()};fs.writeFileSync(p,JSON.stringify(info,null,2));"

# ---- Backend runtime ----
FROM python:3.10-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 ffmpeg git curl && \
    rm -rf /var/lib/apt/lists/*

# copy backend & install deps
COPY backend /app/backend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
# Heavy (best-effort; optional)
RUN pip install --no-cache-dir -r /app/backend/requirements-heavy.txt || echo "⚠️ Skipping heavy stack install"

# copy frontend build
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# args -> env for diagnostics
ARG BUILD_TAG=""
ARG IMAGE_TAG=""
ARG GIT_SHA=""
ENV BUILD_TAG=${BUILD_TAG} IMAGE_TAG=${IMAGE_TAG} GIT_SHA=${GIT_SHA}

EXPOSE 8000

# Health probe tries /health then /api/health
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD (curl -fsS http://127.0.0.1:8000/health || curl -fsS http://127.0.0.1:8000/api/health) >/dev/null || exit 1

# Run the app
CMD ["python","-m","uvicorn","backend.main:app","--host","0.0.0.0","--port","8000","--log-level","info"]