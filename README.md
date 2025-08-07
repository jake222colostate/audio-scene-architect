# SoundForge.AI - Cinematic Audio Generation

A web application that generates cinematic audio using AI models. Users can input scene descriptions and get back high-quality music with layered sound effects.

## 🎯 Features

- **Text-to-Audio Generation**: Describe a scene and get cinematic audio
- **AI-Powered**: Uses Meta's AudioCraft for music and AudioLDM for sound effects
- **Layered Audio**: Automatically combines music with ambient sound effects
- **Multiple Durations**: Support for 30, 60, 90, and 120-second audio clips
- **Web Interface**: Clean React + TailwindCSS frontend
- **Real-time Preview**: Audio player with download functionality

## 🏗️ Architecture

### Frontend (React + Vite)
- Modern React with TypeScript
- TailwindCSS for styling
- Responsive design with audio player
- Real-time audio generation feedback

### Backend (FastAPI + AI Models)
- **AudioCraft (musicgen-small)**: Music generation from text
- **AudioLDM**: Sound effects generation
- **Audio Processing**: pydub for audio layering and export
- **File Management**: Automatic MP3 conversion and serving

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** with pip
2. **Node.js 16+** with npm/yarn
3. **ffmpeg** installed and in PATH
4. **CUDA** (optional but recommended for faster AI inference)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd soundforge-ai
   ```

2. **Install Python dependencies**
   ```bash
   # Make the installation script executable
   chmod +x install_dependencies.sh
   
   # Run the installation (this may take 10-15 minutes)
   ./install_dependencies.sh
   ```

3. **Install frontend dependencies**
   ```bash
   npm install
   ```

### Running the Application

1. **Start the backend server**
   ```bash
   # Activate the virtual environment
   source .venv/bin/activate
   
   # Run the backend
   cd backend
   python run_backend.py
   ```
   
   The backend will start on `http://localhost:8000`

2. **Start the frontend** (in a new terminal)
   ```bash
   npm run dev
   ```
   
   The frontend will start on `http://localhost:8080`

3. **Test the connection**
   - Open your browser to `http://localhost:8080`
   - Try generating audio with a prompt like "A haunted forest with whispers"
   - Check the backend logs for detailed processing information

## 🔧 Configuration

### Backend Configuration

The backend automatically:
- Downloads AI model weights on first run
- Creates required directories (`output_audio`, `sample_audio`, `uploads`)
- Configures CORS for frontend communication
- Sets up detailed logging for debugging

### Environment Variables (Optional)

```bash
# Model cache directory (optional)
export AUDIOCRAFT_CACHE_DIR="/path/to/cache"

# Audio output directory (optional)
export AUDIO_OUTPUT_DIR="/path/to/output"
```

## 🧪 Testing

### Backend Health Check
```bash
curl http://localhost:8000/diagnostic
```

### Test Audio Generation
```bash
curl -X POST http://localhost:8000/test-audio
```

### Manual API Test
```bash
curl -X POST http://localhost:8000/generate-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Epic battle scene with orchestral music", "duration": 30}'
```

## 📁 Project Structure

```
soundforge-ai/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── run_backend.py       # Backend startup script
│   ├── requirements.txt     # Python dependencies
│   ├── output_audio/        # Generated audio files
│   ├── sample_audio/        # Sample/fallback audio
│   └── uploads/             # Video uploads (for future features)
├── src/
│   ├── components/          # React components
│   ├── pages/               # Page components
│   ├── lib/                 # Utilities
│   └── assets/              # Static assets
├── install_dependencies.sh  # Automated setup script
└── README.md               # This file
```

## 🐛 Troubleshooting

### Common Issues

1. **AudioCraft Installation Failed**
   ```bash
   # Try installing PyTorch first
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # Then install AudioCraft
   pip install -U audiocraft
   ```

2. **AudioLDM Not Working**
   ```bash
   # Install from source
   pip install git+https://github.com/haoheliu/AudioLDM.git
   ```

3. **ffmpeg Not Found**
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

4. **Memory Issues**
   - The AI models require significant RAM/VRAM
   - Consider reducing duration or using smaller models
   - Monitor system resources during generation

### Logs and Debugging

- **Backend logs**: Check the terminal running `python run_backend.py`
- **Error logs**: `backend/error_log.txt`
- **Audio generation logs**: `backend/audio_logs.txt`
- **Frontend logs**: Browser developer console

### Performance Optimization

1. **Use CUDA if available** (significant speedup)
2. **Keep models loaded** (backend caches models after first use)
3. **Monitor disk space** (generated audio files can accumulate)

## 🎨 Usage Examples

### Basic Generation
- **Prompt**: "A peaceful forest with birds chirping"
- **Duration**: 60 seconds
- **Result**: Ambient forest music with bird sound effects

### Cinematic Scenes
- **Prompt**: "Epic space battle with laser sounds and dramatic orchestra"
- **Duration**: 90 seconds
- **Result**: Orchestral music with sci-fi sound effects

### Horror Atmosphere
- **Prompt**: "Creepy abandoned hospital with whispers and footsteps"
- **Duration**: 120 seconds
- **Result**: Dark ambient music with horror sound effects

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Meta Research** for AudioCraft
- **AudioLDM Team** for sound effects generation
- **FastAPI** and **React** communities
- **Lovable.dev** for development platform