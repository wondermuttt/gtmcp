#!/bin/bash

# Georgia Tech MCP Server Startup Script
# This script starts the MCP server for ChatGPT integration

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Georgia Tech MCP Server..."

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

# Set environment variables
export MCP_HOST="0.0.0.0"
export MCP_PORT="8080"
export SSL_CERT="/etc/letsencrypt/live/wmjump1.henkelman.net/fullchain.pem"
export SSL_KEY="/etc/letsencrypt/live/wmjump1.henkelman.net/privkey.pem"

# Check if SSL certificates exist
if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "🔐 SSL certificates found, server will use HTTPS"
    SERVER_URL="https://wmjump1.henkelman.net:$MCP_PORT"
else
    echo "⚠️  SSL certificates not found, server will use HTTP"
    SERVER_URL="http://localhost:$MCP_PORT"
fi

# Start the MCP server
echo "🌐 Starting MCP server..."
echo "📡 Server will run on: $SERVER_URL"
echo ""
echo "🔗 MCP SSE Endpoint: $SERVER_URL/sse/"
echo ""
echo "📋 Available Tools:"
echo "  • search - Search for GT courses and research papers"
echo "  • fetch - Retrieve full details for a specific result"
echo ""
echo "🌟 Features:"
echo "  • ✅ MCP Protocol compliant"
echo "  • ✅ SSE transport for remote access"
echo "  • ✅ OSCAR course search"
echo "  • ✅ SMARTech research search"
echo "  • ✅ SSL/HTTPS enabled"
echo ""
echo "💡 To use in ChatGPT:"
echo "  1. Go to ChatGPT Settings → Connectors"
echo "  2. Add custom MCP server"
echo "  3. Server URL: $SERVER_URL/sse/"
echo ""
echo "🔄 Press Ctrl+C to stop"
echo ""

python -m gtmcp.mcp_server