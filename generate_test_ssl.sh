#!/bin/bash

# Generate temporary SSL certificates for testing
# This creates self-signed certificates - replace with Let's Encrypt in production

set -e

echo "🔐 Generating temporary SSL certificates for testing..."

# Create ssl directory if it doesn't exist
mkdir -p ssl

# Generate private key
echo "Generating private key..."
openssl genrsa -out ssl/server.key 2048

# Generate certificate signing request
echo "Generating certificate signing request..."
openssl req -new -key ssl/server.key -out ssl/server.csr -subj "/C=US/ST=Georgia/L=Atlanta/O=Georgia Tech MCP Server/OU=Testing/CN=wmjump1.henkelman.net"

# Generate self-signed certificate (valid for 365 days)
echo "Generating self-signed certificate..."
openssl x509 -req -days 365 -in ssl/server.csr -signkey ssl/server.key -out ssl/server.crt

# Set appropriate permissions
chmod 600 ssl/server.key
chmod 644 ssl/server.crt

echo "✅ SSL certificates generated:"
echo "  Certificate: ssl/server.crt"
echo "  Private Key: ssl/server.key"
echo ""
echo "⚠️  These are self-signed certificates for testing only!"
echo "   For production, replace with Let's Encrypt certificates."
echo ""
echo "🔧 To enable SSL, update config.json:"
echo '  "ssl_enabled": true,'
echo '  "ssl_certfile": "ssl/server.crt",'
echo '  "ssl_keyfile": "ssl/server.key"'