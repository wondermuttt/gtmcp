#!/bin/bash

# Georgia Tech FastAPI Server with SSL/HTTPS Support
# This script starts the HTTPS server with SSL certificates

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Georgia Tech FastAPI Server with SSL/HTTPS..."

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
SSL_CERT=${3:-/etc/letsencrypt/live/wmjump1.henkelman.net/fullchain.pem}
SSL_KEY=${4:-/etc/letsencrypt/live/wmjump1.henkelman.net/privkey.pem}

# Check if SSL certificates exist
if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
    echo "❌ Error: SSL certificates not found!"
    echo "   Certificate: $SSL_CERT"
    echo "   Private Key: $SSL_KEY"
    echo ""
    echo "💡 To set up SSL certificates, run:"
    echo "   sudo ./setup_ssl.sh"
    echo ""
    echo "This will automatically:"
    echo "  • Install Let's Encrypt certbot"
    echo "  • Obtain SSL certificates for wmjump1.henkelman.net"
    echo "  • Configure automatic renewal"
    echo "  • Set up nginx reverse proxy (optional)"
    exit 1
fi

# Check if config file exists
CONFIG_ARG=""
if [ -f "config.json" ]; then
    CONFIG_ARG="--config config.json"
    echo "📄 Using config.json"
else
    echo "⚠️  Warning: config.json not found, using defaults"
fi

# Start the FastAPI server with SSL
echo "🔐 Starting FastAPI server with SSL/HTTPS..."
echo "📡 Server will run on: https://$HOST:$PORT"
echo "🔑 SSL Certificate: $SSL_CERT"
echo "🔑 SSL Private Key: $SSL_KEY"
echo ""
echo "🔗 ChatGPT Integration URL: https://wmjump1.henkelman.net:$PORT"
echo ""
echo "📋 Available Endpoints:"
echo "  • GET  / - Server info"
echo "  • GET  /health - Health check"
echo "  • GET  /.well-known/ai-plugin.json - ChatGPT plugin manifest"
echo "  • GET  /openapi.json - OpenAPI specification"
echo "  • GET  /docs - Interactive API documentation"
echo ""
echo "🌟 FEATURES:"
echo "  • ✅ SSL/HTTPS enabled"
echo "  • ✅ OSCAR Course Search (500 error fixes applied)"
echo "  • ✅ Research Paper Search"
echo "  • ✅ JSON API responses"
echo "  • ✅ CORS enabled for ChatGPT"
echo ""
echo "🔄 Press Ctrl+C to stop"
echo ""

python -m gtmcp.server_fastapi \
    --host "$HOST" \
    --port "$PORT" \
    --ssl \
    --ssl-cert "$SSL_CERT" \
    --ssl-key "$SSL_KEY" \
    $CONFIG_ARG "$@"