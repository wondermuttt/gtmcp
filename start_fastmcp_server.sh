#!/bin/bash

# Georgia Tech FastMCP Server Startup Script

# Activate conda environment
source ~/miniforge3/etc/profile.d/conda.sh
conda activate gtmcp

# Set environment variables
export MCP_HOST="0.0.0.0"
export MCP_PORT="8080"
export SSL_CERT="/etc/letsencrypt/live/wmjump1.henkelman.net/fullchain.pem"
export SSL_KEY="/etc/letsencrypt/live/wmjump1.henkelman.net/privkey.pem"

# Change to project directory
cd /home/wondermutt/gtmcp

# Start the FastMCP server
echo "Starting Georgia Tech FastMCP Server..."
echo "Server will be available at:"
echo "  - https://wmjump1.henkelman.net:8080/sse/"
echo ""
echo "Add this URL to ChatGPT as a custom MCP server"
echo ""

# Run the server
python -m gtmcp.fastmcp_server