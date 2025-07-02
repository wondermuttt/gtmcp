#!/bin/bash

# SSL Setup Script for Georgia Tech MCP Server
# This script sets up Let's Encrypt SSL certificates for wmjump1.henkelman.net
# and configures the application to use them

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
WEBROOT_PATH="/var/www/certbot"

echo -e "${GREEN}Let's Encrypt SSL Setup for ${DOMAIN}${NC}"
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
    apt-get install -y certbot python3-certbot-nginx
else
    echo "Certbot is already installed"
fi

# Create webroot directory for certbot challenges
echo -e "${YELLOW}Creating webroot directory...${NC}"
mkdir -p ${WEBROOT_PATH}
chown -R www-data:www-data ${WEBROOT_PATH}

# Check if nginx is installed and running
if command_exists nginx && systemctl is-active --quiet nginx; then
    echo -e "${YELLOW}Nginx is running. Creating temporary configuration for certbot...${NC}"
    
    # Create a temporary nginx config for certbot verification
    cat > /etc/nginx/sites-available/certbot-temp << EOF
server {
    listen 80;
    server_name ${DOMAIN};
    
    location /.well-known/acme-challenge/ {
        root ${WEBROOT_PATH};
    }
    
    location / {
        return 404;
    }
}
EOF
    
    # Enable the temporary site
    ln -sf /etc/nginx/sites-available/certbot-temp /etc/nginx/sites-enabled/
    nginx -s reload
    
    # Obtain certificate using webroot
    echo -e "${YELLOW}Obtaining SSL certificate...${NC}"
    certbot certonly \
        --webroot \
        --webroot-path=${WEBROOT_PATH} \
        --email ${EMAIL} \
        --agree-tos \
        --no-eff-email \
        --domains ${DOMAIN} \
        --non-interactive
    
    # Remove temporary nginx config
    rm -f /etc/nginx/sites-enabled/certbot-temp
    rm -f /etc/nginx/sites-available/certbot-temp
    nginx -s reload
else
    # Use standalone mode if nginx is not running
    echo -e "${YELLOW}Using standalone mode for certificate generation...${NC}"
    echo -e "${RED}Note: This requires port 80 to be free${NC}"
    
    certbot certonly \
        --standalone \
        --email ${EMAIL} \
        --agree-tos \
        --no-eff-email \
        --domains ${DOMAIN} \
        --non-interactive
fi

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

# Set up auto-renewal
echo -e "${YELLOW}Setting up auto-renewal...${NC}"
cat > /etc/systemd/system/certbot-renewal.service << EOF
[Unit]
Description=Let's Encrypt renewal

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --deploy-hook "systemctl reload nginx"
EOF

cat > /etc/systemd/system/certbot-renewal.timer << EOF
[Unit]
Description=Twice daily renewal of Let's Encrypt's certificates

[Timer]
OnCalendar=0/12:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable certbot-renewal.timer
systemctl start certbot-renewal.timer

# Create nginx configuration for the application (if nginx is installed)
if command_exists nginx; then
    echo -e "${YELLOW}Creating nginx configuration for MCP server...${NC}"
    cat > /etc/nginx/sites-available/gtmcp << EOF
server {
    listen 80;
    server_name ${DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};
    
    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    
    # SSL session caching
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Proxy to FastAPI application
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
    
    # Enable the site
    ln -sf /etc/nginx/sites-available/gtmcp /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    nginx -t
    
    # Reload nginx
    systemctl reload nginx
    
    echo -e "${GREEN}Nginx configuration created and enabled${NC}"
fi

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
echo "2. Or use nginx as a reverse proxy (already configured)"
echo ""
echo "3. Update your ChatGPT configuration to use:"
echo "   https://${DOMAIN}"
echo ""
echo "Auto-renewal is configured and will run twice daily."
echo ""
echo -e "${YELLOW}Note: Make sure port 443 is open in your firewall!${NC}"