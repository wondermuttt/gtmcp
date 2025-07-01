#!/bin/bash

# Georgia Tech Expanded MCP Server Startup Script
# This script activates the conda environment and starts the expanded multi-system server

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Georgia Tech Expanded MCP Server (Multi-System Integration)..."

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

# Check if config file exists
if [ ! -f "config.json" ]; then
    echo "⚠️  Warning: config.json not found, using defaults"
fi

# Parse command line arguments
CONFIG_ARG=""
if [ -f "config.json" ]; then
    CONFIG_ARG="--config config.json"
fi

# Start the expanded server
echo "🌐 Starting Expanded MCP server..."
echo "📡 Server will run on the configured host:port (default: 0.0.0.0:8080)"
echo ""
echo "🌟 EXPANDED FEATURES ACTIVE:"
echo "  • OSCAR Course Scheduling"
echo "  • SMARTech Research Repository"
echo "  • GT Places Campus Information"
echo "  • Cross-System Integration"
echo "  • 17 Comprehensive MCP Tools"
echo ""
echo "🔄 Press Ctrl+C to stop"
echo ""

python -m gtmcp.server_expanded $CONFIG_ARG "$@"