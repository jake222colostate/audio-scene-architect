# ---- Frontend build ----
FROM node:20-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . ./
RUN npm run build

# ---- Backend runtime ----
FROM python:3.11-slim AS runtime
ARG HEAVY=0
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app
# System deps for soundfile/libsndfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Copy backend
COPY backend /app/backend
RUN pip install --no-cache-dir -r backend/requirements.txt

# Optionally install heavy deps
RUN if [ "$HEAVY" = "1" ]; then pip install --no-cache-dir -r backend/requirements-heavy.txt; fi

# Copy frontend dist (if present)
RUN mkdir -p /app/frontend/dist
COPY --from=frontend /app/dist /app/frontend/dist

# Prove what's inside the image (shallow tree)
RUN python -c "import glob; print('DEBUG tree:'); [print(p) for p in glob.glob('/app/**', recursive=True) if p.count('/')<6]"

# Launch
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health >/dev/null || exit 1
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
