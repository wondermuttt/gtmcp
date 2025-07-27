#!/bin/bash

# SSL Setup Script for Georgia Tech MCP Server using DNS Challenge
# This script sets up Let's Encrypt SSL certificates for wmjump1.henkelman.net
# using DNS-01 challenge which doesn't require port 80 to be open

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="wmjump1.henkelman.net"
EMAIL="${LETSENCRYPT_EMAIL:-admin@henkelman.net}"  # Can be overridden with environment variable
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
APP_CERT_DIR="/home/phenkelm/src/gtmcp/certs"

echo -e "${GREEN}Let's Encrypt SSL Setup for ${DOMAIN} (DNS Challenge)${NC}"
echo "========================================"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run this script with sudo${NC}"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install certbot if not already installed
echo -e "${YELLOW}Checking for certbot...${NC}"
if ! command_exists certbot; then
    echo "Installing certbot..."
    apt-get update
    apt-get install -y certbot
else
    echo "Certbot is already installed"
fi

# Use DNS challenge
echo -e "${YELLOW}Using DNS challenge for certificate generation...${NC}"
echo -e "${GREEN}This method doesn't require any ports to be open!${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: You'll need to add a TXT record to your DNS.${NC}"
echo -e "${YELLOW}The script will pause and show you what record to add.${NC}"
echo ""

# Run certbot with manual DNS challenge
certbot certonly \
    --manual \
    --preferred-challenges dns \
    --email ${EMAIL} \
    --agree-tos \
    --no-eff-email \
    --domains ${DOMAIN} \
    --manual-public-ip-logging-ok

# Check if certificate was obtained successfully
if [ ! -d "${CERT_DIR}" ]; then
    echo -e "${RED}Certificate generation failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Certificate obtained successfully!${NC}"

# Create directory for application certificates
echo -e "${YELLOW}Setting up application certificate directory...${NC}"
mkdir -p ${APP_CERT_DIR}
chown phenkelm:phenkelm ${APP_CERT_DIR}

# Create symbolic links to the certificates
echo -e "${YELLOW}Creating certificate links for application...${NC}"
ln -sf ${CERT_DIR}/fullchain.pem ${APP_CERT_DIR}/fullchain.pem
ln -sf ${CERT_DIR}/privkey.pem ${APP_CERT_DIR}/privkey.pem

# Set up auto-renewal (note: DNS renewal requires manual intervention or automation)
echo -e "${YELLOW}Setting up renewal reminder...${NC}"
cat > /etc/systemd/system/certbot-renewal.service << EOF
[Unit]
Description=Let's Encrypt renewal check

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --dry-run
EOF

cat > /etc/systemd/system/certbot-renewal.timer << EOF
[Unit]
Description=Monthly check of Let's Encrypt's certificates

[Timer]
OnCalendar=monthly
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable certbot-renewal.timer
systemctl start certbot-renewal.timer

# Update the application configuration to use SSL
echo -e "${YELLOW}Updating application configuration...${NC}"

# Create SSL configuration for the application
cat > ${APP_CERT_DIR}/ssl_config.json << EOF
{
  "ssl": {
    "enabled": true,
    "cert_file": "${APP_CERT_DIR}/fullchain.pem",
    "key_file": "${APP_CERT_DIR}/privkey.pem",
    "domain": "${DOMAIN}"
  }
}
EOF

chown phenkelm:phenkelm ${APP_CERT_DIR}/ssl_config.json

# Display summary
echo -e "${GREEN}SSL Setup Complete!${NC}"
echo "========================================"
echo "Domain: ${DOMAIN}"
echo "Certificate directory: ${CERT_DIR}"
echo "Application cert links: ${APP_CERT_DIR}"
echo ""
echo "Next steps:"
echo "1. The FastAPI server can now use SSL directly with:"
echo "   --ssl-cert ${APP_CERT_DIR}/fullchain.pem --ssl-key ${APP_CERT_DIR}/privkey.pem"
echo ""
echo "2. Update your ChatGPT configuration to use:"
echo "   https://${DOMAIN}:8080"
echo ""
echo -e "${YELLOW}Note: DNS challenge renewal requires manual intervention.${NC}"
echo -e "${YELLOW}Consider setting up automated DNS updates with your provider.${NC}"