#!/bin/bash

echo "🚀 Setting up Ollama RAG System..."

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it first using:"
    echo "curl https://ollama.ai/install.sh | sh"
    exit 1
fi

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install it first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Make guria script executable
echo "🔑 Setting executable permissions for guria..."
chmod +x guria

# Check if Ollama service is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "⚠️ Ollama service is not running. Starting it..."
    ollama serve &
    sleep 5  # Wait for Ollama to start
fi

# Pull the DeepSeek models
echo "🤖 Pulling DeepSeek-R1 models..."
echo "Pulling 8B model (recommended)..."
ollama pull deepseek-r1:8b

echo "✅ Setup complete!"
echo "To start the RAG system, run: ./guria.sh"
