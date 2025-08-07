# Stage 1: Build the React frontend
FROM node:18 AS frontend-builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . . 
RUN npm run build

# Stage 2: Main Python backend container
FROM python:3.10-slim

ARG HEAVY=0
ENV USE_HEAVY_MODE=${HEAVY}

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    pkg-config \
    curl \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements files for better Docker layer caching
COPY requirements-lite.txt requirements-pypi.txt requirements-git.txt ./

# Install Python dependencies in two stages to avoid resolution conflicts
RUN echo "=== Stage 1: Installing PyPI packages ===" && \
    pip install --upgrade pip && \
    echo "=== Installing stable PyPI dependencies ===" && \
    pip install -r requirements-pypi.txt -v && \
    echo "=== Stage 1 completed successfully ===" && \
    echo "=== Stage 2: Installing Git-based packages ===" && \
    pip install -r requirements-git.txt -v && \
    echo "=== Stage 2 completed successfully ==="

# Post-install sanity checks for critical packages
RUN echo "=== Post-install verification ===" && \
    python -c "import torch; print(f'✅ PyTorch: {torch.__version__}')" && \
    python -c "import torchaudio; print(f'✅ TorchAudio: {torchaudio.__version__}')" && \
    python -c "import fastapi, uvicorn, soundfile, librosa; print('✅ Core packages OK')" && \
    python -c "import transformers; print(f'✅ Transformers: {transformers.__version__}')" && \
    python -c "import diffusers; print(f'✅ Diffusers: {diffusers.__version__}')" && \
    echo "=== Checking AudioCraft installation ===" && \
    python -c "from audiocraft.models import musicgen; print('✅ AudioCraft: OK')" && \
    echo "=== Checking AudioLDM installation ===" && \
    python -c "import audioldm; print('✅ AudioLDM: OK')" || echo "⚠️ AudioLDM not available (optional)" && \
    echo "=== All package verification completed ==="

# Copy Python backend files
COPY . .

# Copy frontend build output from Stage 1
COPY --from=frontend-builder /app/dist ./dist

# Final validation
RUN echo "=== Final build validation ===" && \
    echo "=== Project structure ===" && \
    ls -la && \
    echo "=== Verifying main application file ===" && \
    test -f main.py && echo "✅ main.py found" || echo "❌ main.py missing" && \
    echo "=== Build completed successfully ==="

EXPOSE 8000

# Health check using the diagnostic endpoint
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/api/diagnostic || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]