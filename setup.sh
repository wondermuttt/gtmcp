#!/bin/bash

# Georgia Tech MCP Server Setup Script
# This script sets up the conda environment and installs dependencies

set -e  # Exit on any error

echo "🚀 Setting up Georgia Tech MCP Server..."

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "❌ Error: Conda is not installed or not in PATH"
    echo "Please install Anaconda or Miniconda first:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✅ Conda found: $(conda --version)"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📂 Working in: $SCRIPT_DIR"

# Check if environment already exists
if conda env list | grep -q "^gtmcp "; then
    echo "⚠️  Environment 'gtmcp' already exists"
    read -p "Do you want to remove and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing environment..."
        conda env remove -n gtmcp -y
    else
        echo "✋ Keeping existing environment"
        echo "💡 To activate: conda activate gtmcp"
        exit 0
    fi
fi

# Create conda environment
echo "🐍 Creating conda environment 'gtmcp' with Python 3.11..."
conda create -n gtmcp python=3.11 -y

# Activate environment and install dependencies
echo "📦 Installing dependencies..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gtmcp

# Install Python dependencies
pip install -r requirements.txt

# Install package in development mode
echo "🔧 Installing gtmcp package in development mode..."
pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Activate the environment:"
echo "     conda activate gtmcp"
echo ""
echo "  2. Test the setup:"
echo "     python test_server.py"
echo ""
echo "  3. Run the MCP server:"
echo "     python -m gtmcp.server"
echo ""
echo "  4. Or run with custom config:"
echo "     python -m gtmcp.server --config config.json"
echo ""
echo "📚 See README.md for more details"