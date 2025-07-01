#!/bin/bash

# Georgia Tech HTTP MCP Server Startup Script for ChatGPT Integration
# This script activates the conda environment and starts the HTTP-based MCP server

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Georgia Tech HTTP MCP Server for ChatGPT Integration..."

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

# Start the HTTP server
echo "🌐 Starting HTTP MCP server for ChatGPT..."
echo "📡 Server will run on: http://$HOST:$PORT"
echo ""
echo "🔗 ChatGPT Integration URL: http://$HOST:$PORT"
echo ""
echo "📋 ChatGPT Setup Instructions:"
echo "  1. Open ChatGPT settings"
echo "  2. Go to Connectors → Custom"
echo "  3. Add new tool with URL: http://$HOST:$PORT"
echo "  4. Name: Georgia Tech MCP Server"
echo "  5. Description: Access GT course schedules, research papers, and campus info"
echo ""
echo "🌟 AVAILABLE FEATURES:"
echo "  • OSCAR Course Search (500 error fixes applied)"
echo "  • Research Paper Search"
echo "  • System Health Monitoring"
echo ""
echo "🔄 Press Ctrl+C to stop"
echo ""

python -m gtmcp.server_http --host "$HOST" --port "$PORT" $CONFIG_ARG "$@"