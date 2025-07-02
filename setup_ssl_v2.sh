#!/bin/bash

# SSL Setup Script for Georgia Tech MCP Server - Version 2
# This script sets up Let's Encrypt SSL certificates for wmjump1.henkelman.net
# with improved error handling and diagnostics

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="wmjump1.henkelman.net"
EMAIL="${LETSENCRYPT_EMAIL:-admin@henkelman.net}"  # Can be overridden with environment variable
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
APP_CERT_DIR="/home/phenkelm/src/gtmcp/certs"
WEBROOT_PATH="/var/www/certbot"

echo -e "${GREEN}Let's Encrypt SSL Setup for ${DOMAIN} - Version 2${NC}"
echo "=============================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run this script with sudo${NC}"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check DNS resolution
check_dns() {
    echo -e "${BLUE}Checking DNS resolution for ${DOMAIN}...${NC}"
    
    # Get server's public IP
    SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "unknown")
    echo "Server's public IP: ${SERVER_IP}"
    
    # Check DNS resolution
    DNS_IP=$(dig +short ${DOMAIN} | tail -n1)
    if [ -z "$DNS_IP" ]; then
        echo -e "${RED}Error: Cannot resolve ${DOMAIN}${NC}"
        echo "Please ensure your DNS A record is configured properly."
        return 1
    fi
    
    echo "Domain resolves to: ${DNS_IP}"
    
    if [ "$SERVER_IP" != "$DNS_IP" ] && [ "$SERVER_IP" != "unknown" ]; then
        echo -e "${YELLOW}Warning: Domain IP ($DNS_IP) doesn't match server IP ($SERVER_IP)${NC}"
        echo "This might cause certificate validation to fail."
        read -p "Do you want to continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}DNS configuration looks good!${NC}"
    fi
}

# Check DNS before proceeding
check_dns

# Install certbot if not already installed
echo -e "${YELLOW}Checking for certbot...${NC}"
if ! command_exists certbot; then
    echo "Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
else
    echo "Certbot is already installed"
    # Update certbot to latest version
    echo "Updating certbot..."
    apt-get update && apt-get install -y --only-upgrade certbot
fi

# Check if we have existing certificates
if [ -d "${CERT_DIR}" ]; then
    echo -e "${YELLOW}Existing certificates found for ${DOMAIN}${NC}"
    read -p "Do you want to renew/reconfigure? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping certificate generation, proceeding with configuration..."
        SKIP_CERT_GEN=true
    fi
fi

# Clean up any previous failed attempts
if [ "$SKIP_CERT_GEN" != "true" ]; then
    echo -e "${YELLOW}Cleaning up any previous configurations...${NC}"
    certbot delete --cert-name ${DOMAIN} --non-interactive 2>/dev/null || true
fi

# Check what's using port 80
echo -e "${BLUE}Checking port 80 availability...${NC}"
if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}Port 80 is in use by:${NC}"
    lsof -Pi :80 -sTCP:LISTEN
    
    # Check if it's nginx
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}Nginx is running - will use nginx plugin${NC}"
        USE_NGINX=true
    else
        echo -e "${RED}Port 80 is in use by another service${NC}"
        echo "Please free up port 80 or stop the service using it."
        exit 1
    fi
else
    echo -e "${GREEN}Port 80 is available${NC}"
    USE_STANDALONE=true
fi

# Generate certificate
if [ "$SKIP_CERT_GEN" != "true" ]; then
    echo -e "${YELLOW}Obtaining SSL certificate...${NC}"
    
    if [ "$USE_NGINX" = "true" ]; then
        # Use nginx plugin
        echo "Using nginx plugin..."
        certbot certonly \
            --nginx \
            --email ${EMAIL} \
            --agree-tos \
            --no-eff-email \
            --domains ${DOMAIN} \
            --non-interactive \
            --keep-until-expiring \
            --expand
    else
        # Use standalone mode
        echo "Using standalone mode..."
        certbot certonly \
            --standalone \
            --email ${EMAIL} \
            --agree-tos \
            --no-eff-email \
            --domains ${DOMAIN} \
            --non-interactive \
            --keep-until-expiring \
            --expand
    fi
    
    # Check if certificate was obtained successfully
    if [ ! -d "${CERT_DIR}" ]; then
        echo -e "${RED}Certificate generation failed!${NC}"
        echo "Checking certbot logs..."
        tail -n 50 /var/log/letsencrypt/letsencrypt.log
        exit 1
    fi
    
    echo -e "${GREEN}Certificate obtained successfully!${NC}"
fi

# Create directory for application certificates
echo -e "${YELLOW}Setting up application certificate directory...${NC}"
mkdir -p ${APP_CERT_DIR}
chown phenkelm:phenkelm ${APP_CERT_DIR}

# Create symbolic links to the certificates
echo -e "${YELLOW}Creating certificate links for application...${NC}"
ln -sf ${CERT_DIR}/fullchain.pem ${APP_CERT_DIR}/fullchain.pem
ln -sf ${CERT_DIR}/privkey.pem ${APP_CERT_DIR}/privkey.pem

# Verify certificate links
if [ -L "${APP_CERT_DIR}/fullchain.pem" ] && [ -L "${APP_CERT_DIR}/privkey.pem" ]; then
    echo -e "${GREEN}Certificate links created successfully${NC}"
else
    echo -e "${RED}Failed to create certificate links${NC}"
    exit 1
fi

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
    
    # Backup existing config if it exists
    if [ -f /etc/nginx/sites-available/gtmcp ]; then
        cp /etc/nginx/sites-available/gtmcp /etc/nginx/sites-available/gtmcp.backup
        echo "Backed up existing nginx config to gtmcp.backup"
    fi
    
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
    
    # Remove default site if it exists
    rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    echo -e "${BLUE}Testing nginx configuration...${NC}"
    if nginx -t; then
        echo -e "${GREEN}Nginx configuration is valid${NC}"
        systemctl reload nginx
    else
        echo -e "${RED}Nginx configuration has errors${NC}"
        echo "Please check the configuration and fix any issues."
    fi
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

# Test certificate
echo -e "${BLUE}Testing SSL certificate...${NC}"
openssl x509 -in ${CERT_DIR}/fullchain.pem -text -noout | grep -E "(Subject:|DNS:|Not After)"

# Display summary
echo ""
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
if command_exists nginx; then
    echo "2. Nginx is configured as a reverse proxy"
    echo "   HTTP (port 80) → HTTPS redirect"
    echo "   HTTPS (port 443) → FastAPI on port 8080"
    echo ""
fi
echo "3. Update your ChatGPT configuration to use:"
if command_exists nginx; then
    echo "   https://${DOMAIN}"
else
    echo "   https://${DOMAIN}:8080"
fi
echo ""
echo "Auto-renewal is configured and will run twice daily."
echo ""
echo -e "${YELLOW}Important: Make sure ports 80 and 443 are open in your firewall!${NC}"
echo ""
echo "To test the server with SSL:"
echo "  ./start_server_ssl.sh"
echo ""
echo "To run as a system service:"
echo "  sudo cp gtmcp-ssl.service /etc/systemd/system/"
echo "  sudo systemctl enable gtmcp-ssl"
echo "  sudo systemctl start gtmcp-ssl"