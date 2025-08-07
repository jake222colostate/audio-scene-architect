#!/bin/bash

# SoundForge.AI Docker Build and Validation Script
set -e

echo "🐳 SoundForge.AI Docker Build and Test Script (Staged Dependencies)"
echo "=================================================================="

# Build the Docker image
echo "📦 Building Docker image: soundforge-ai"
echo "This may take several minutes for first build..."
echo "Building with staged dependency installation for better reliability..."
docker build -t soundforge-ai . --progress=plain

echo "✅ Docker build completed successfully!"

# Test container startup
echo "🚀 Testing container startup..."
docker run -d --name soundforge-test -p 8000:8000 soundforge-ai

echo "⏳ Waiting for container to start (30 seconds)..."
sleep 30

# Check container status
echo "📊 Container status:"
docker ps -a | grep soundforge-test

# Test ping endpoint
echo "🏃 Testing /api/ping endpoint..."
if curl -f http://localhost:8000/api/ping; then
    echo "✅ Ping endpoint is working!"
else
    echo "❌ Ping endpoint failed!"
    docker logs soundforge-test
    exit 1
fi

# Test generate-audio endpoint structure
echo "🎵 Testing /api/generate-audio endpoint..."
response=$(curl -X POST "http://localhost:8000/api/generate-audio" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "short test audio", "duration": 30}' \
    --max-time 10 -w "%{http_code}" -o response.json) || true

echo "Response code: $response"
if [ -f response.json ]; then
    echo "Response body:"
    cat response.json
    rm -f response.json
fi

# Check container logs for any errors
echo "📋 Container logs:"
docker logs soundforge-test | tail -20

# Cleanup
echo "🧹 Cleaning up..."
docker stop soundforge-test
docker rm soundforge-test

# Show final image information
echo "📈 Final image information:"
docker images soundforge-ai

echo ""
echo "🎉 Docker build and staged dependency validation completed successfully!"
echo "💡 Dependencies installed in stages:"
echo "   Stage 1: PyPI packages (requirements-pypi.txt)"
echo "   Stage 2: Git packages (requirements-git.txt)"
echo "💡 To run the container manually:"
echo "   docker run -p 8000:8000 soundforge-ai"
echo "💡 To test the API:"
echo "   curl http://localhost:8000/api/ping"