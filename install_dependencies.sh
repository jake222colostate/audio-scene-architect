#!/usr/bin/env bash
set -e

echo "🎵 SoundForge.AI - Enhanced Dependency Installation..."

# Check Python version
python_version=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
required_version=3.8
if [[ $(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1) != "$required_version" ]]; then
  echo "❌ Python $required_version or higher is required. Current version: $python_version" >&2
  exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check system resources
echo "💾 Checking system resources..."
python3 -c "
import psutil
ram_gb = psutil.virtual_memory().total / (1024**3)
available_gb = psutil.virtual_memory().available / (1024**3)
print(f'Total RAM: {ram_gb:.1f} GB')
print(f'Available RAM: {available_gb:.1f} GB')
if available_gb < 2.0:
    print('⚠️ Warning: Less than 2GB RAM available. MusicGen may fail to load.')
if available_gb < 4.0:
    print('💡 Recommendation: Use GPU-enabled environment for optimal performance.')
"

# Create virtual environment if not exists
if [ ! -d .venv ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install system dependencies if on Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Installing system dependencies (requires sudo)..."
    sudo apt-get update && sudo apt-get install -y \
        ffmpeg \
        git \
        libsndfile1 \
        libportaudio2 \
        libasound2-dev \
        build-essential \
        python3-dev \
        || echo "⚠️ Some system packages may be missing. Install ffmpeg manually if needed."
fi

# Install Python dependencies with better error handling
echo "🐍 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install --no-cache-dir -r requirements.txt
elif [ -f "backend/requirements.txt" ]; then
    pip install --no-cache-dir -r backend/requirements.txt
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Verify critical installations
echo "✅ Verifying installations..."

# Check PyTorch
echo "🔥 Checking PyTorch..."
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA devices: {torch.cuda.device_count()}')
    print(f'Current device: {torch.cuda.get_device_name(0)}')
else:
    print('Running on CPU - performance may be limited')
"

# Check AudioCraft
echo "🎵 Checking AudioCraft..."
python3 -c "
try:
    import audiocraft
    from audiocraft.models import musicgen
    print('✅ AudioCraft import successful')
except Exception as e:
    print(f'❌ AudioCraft import failed: {e}')
    exit(1)
"

# Check FFmpeg
echo "🎬 Checking FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    ffmpeg -version | head -n 1
    echo "✅ FFmpeg available"
else
    echo "❌ FFmpeg not found in PATH"
fi

echo ""
echo "🎉 Installation complete!"
echo "💡 Next steps:"
echo "   1. Activate environment: source .venv/bin/activate"
echo "   2. Run the application: python main.py"
echo "   3. For RunPod: Use A10 or T4 GPU for optimal performance"
echo "   4. Minimum 4GB RAM recommended for stable MusicGen operation"

