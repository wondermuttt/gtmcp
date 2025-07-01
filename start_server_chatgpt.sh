#!/bin/bash

# Georgia Tech FastAPI Server for ChatGPT Integration
# This script starts the HTTP server that ChatGPT can connect to

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Georgia Tech FastAPI Server for ChatGPT Integration..."

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Error: Conda not found in PATH"
    exit 1
fi

# Check if gtmcp environment exists
if ! conda env list | grep -q "^gtmcp "; then
    echo "❌ Error: gtmcp environment not found"
    echo "Please run ./setup.sh first to create the environment"
    exit 1
fi

# Activate environment
echo "🐍 Activating conda environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gtmcp

# Parse command line arguments
HOST=${1:-0.0.0.0}
PORT=${2:-8080}

# Check if config file exists
CONFIG_ARG=""
if [ -f "config.json" ]; then
    CONFIG_ARG="--config config.json"
    echo "📄 Using config.json"
else
    echo "⚠️  Warning: config.json not found, using defaults"
fi

# Start the FastAPI server
echo "🌐 Starting FastAPI server for ChatGPT..."
echo "📡 Server will run on: http://$HOST:$PORT"
echo ""
echo "🔗 ChatGPT Integration Setup:"
echo "  1. Open ChatGPT settings"
echo "  2. Go to Beta Features"
echo "  3. Enable 'Custom GPTs & Tools'"
echo "  4. Create new custom tool:"
echo "     • Name: Georgia Tech MCP Server"
echo "     • Description: Access GT course schedules and research"
echo "     • URL: http://$HOST:$PORT"
echo ""
echo "📋 Available Endpoints:"
echo "  • GET  / - Server info"
echo "  • GET  /health - Health check"
echo "  • GET  /api/semesters - Available semesters"
echo "  • GET  /api/subjects/{term_code} - Subjects for semester"
echo "  • GET  /api/courses?term_code=X&subject=Y - Search courses"
echo "  • GET  /api/research?keywords=X - Search research papers"
echo ""
echo "🌟 FEATURES:"
echo "  • ✅ OSCAR Course Search (500 error fixes applied)"
echo "  • ✅ Research Paper Search"
echo "  • ✅ JSON API responses"
echo "  • ✅ CORS enabled for ChatGPT"
echo ""
echo "🔄 Press Ctrl+C to stop"
echo ""

python -m gtmcp.server_fastapi --host "$HOST" --port "$PORT" $CONFIG_ARG "$@"