#!/bin/bash

# Simple SSL Setup Script for Georgia Tech MCP Server
# This version ensures proper HTTP challenge setup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="wmjump1.henkelman.net"
EMAIL="${LETSENCRYPT_EMAIL:-admin@henkelman.net}"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
APP_CERT_DIR="/home/phenkelm/src/gtmcp/certs"

echo -e "${GREEN}Simple SSL Setup for ${DOMAIN}${NC}"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run this script with sudo${NC}"
    exit 1
fi

# Step 1: Stop any services using port 80
echo -e "${YELLOW}Step 1: Checking port 80...${NC}"
if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Services using port 80:"
    lsof -Pi :80 -sTCP:LISTEN
    
    # Check for common services
    for service in nginx apache2 httpd; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            echo -e "${YELLOW}Stopping $service...${NC}"
            systemctl stop $service
        fi
    done
    
    # Check if gtmcp is running on port 80
    if lsof -Pi :80 -sTCP:LISTEN | grep -q python; then
        echo -e "${YELLOW}Python process detected on port 80 (likely gtmcp)${NC}"
        echo "Please stop the gtmcp server temporarily"
        echo "Press Ctrl+C in the server terminal, then press Enter here to continue..."
        read -p ""
    fi
fi

# Verify port 80 is free
if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}Port 80 is still in use. Please free it up before continuing.${NC}"
    exit 1
fi

echo -e "${GREEN}Port 80 is free!${NC}"

# Step 2: Install/update certbot
echo -e "\n${YELLOW}Step 2: Installing/updating certbot...${NC}"
apt-get update
apt-get install -y certbot

# Step 3: Run certbot in standalone mode
echo -e "\n${YELLOW}Step 3: Obtaining certificate...${NC}"
echo "Using standalone mode (certbot will create its own temporary web server)"

# Remove any existing certificates for this domain to start fresh
certbot delete --cert-name ${DOMAIN} --non-interactive 2>/dev/null || true

# Get the certificate
certbot certonly \
    --standalone \
    --preferred-challenges http \
    --email ${EMAIL} \
    --agree-tos \
    --no-eff-email \
    --domain ${DOMAIN} \
    --non-interactive

# Check if successful
if [ ! -d "${CERT_DIR}" ]; then
    echo -e "${RED}Certificate generation failed!${NC}"
    echo "Checking logs..."
    tail -n 30 /var/log/letsencrypt/letsencrypt.log
    exit 1
fi

echo -e "${GREEN}Certificate obtained successfully!${NC}"

# Step 4: Set up certificate links
echo -e "\n${YELLOW}Step 4: Setting up certificate links...${NC}"
mkdir -p ${APP_CERT_DIR}
ln -sf ${CERT_DIR}/fullchain.pem ${APP_CERT_DIR}/fullchain.pem
ln -sf ${CERT_DIR}/privkey.pem ${APP_CERT_DIR}/privkey.pem
chown -R phenkelm:phenkelm ${APP_CERT_DIR}

# Step 5: Set up auto-renewal with pre/post hooks
echo -e "\n${YELLOW}Step 5: Setting up auto-renewal...${NC}"

# Create renewal configuration with hooks
mkdir -p /etc/letsencrypt/renewal-hooks/pre
mkdir -p /etc/letsencrypt/renewal-hooks/post

# Pre-hook: Stop services using port 80
cat > /etc/letsencrypt/renewal-hooks/pre/stop-services.sh << 'EOF'
#!/bin/bash
# Stop services that might be using port 80
for service in nginx apache2 httpd; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        systemctl stop $service
        touch /tmp/certbot-stopped-$service
    fi
done
EOF

# Post-hook: Restart services
cat > /etc/letsencrypt/renewal-hooks/post/start-services.sh << 'EOF'
#!/bin/bash
# Restart services that were stopped
for service in nginx apache2 httpd; do
    if [ -f /tmp/certbot-stopped-$service ]; then
        systemctl start $service
        rm -f /tmp/certbot-stopped-$service
    fi
done
EOF

chmod +x /etc/letsencrypt/renewal-hooks/pre/stop-services.sh
chmod +x /etc/letsencrypt/renewal-hooks/post/start-services.sh

# Set up systemd timer for renewal
cat > /etc/systemd/system/certbot-renewal.timer << EOF
[Unit]
Description=Run certbot twice daily

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable certbot-renewal.timer
systemctl start certbot-renewal.timer

# Step 6: Create simple nginx config (optional)
if command -v nginx >/dev/null 2>&1; then
    echo -e "\n${YELLOW}Step 6: Creating nginx configuration...${NC}"
    
    cat > /etc/nginx/sites-available/gtmcp-ssl << EOF
server {
    listen 80;
    server_name ${DOMAIN};
    
    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect everything else to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};
    
    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    
    # Basic SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    
    # Proxy to your FastAPI app
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/gtmcp-ssl /etc/nginx/sites-enabled/
    nginx -t && systemctl restart nginx
    echo -e "${GREEN}Nginx configured!${NC}"
fi

# Display results
echo -e "\n${GREEN}SSL Setup Complete!${NC}"
echo "========================================"
echo "Certificate location: ${CERT_DIR}"
echo "App certificate links: ${APP_CERT_DIR}"
echo ""
echo "To start your server with SSL:"
echo "  ./start_server_ssl.sh"
echo ""
echo "Or if using nginx proxy:"
echo "  python -m gtmcp.server_fastapi --host 127.0.0.1 --port 8080"
echo "  (nginx will handle SSL on port 443)"
echo ""
echo "Test your SSL setup:"
echo "  curl https://${DOMAIN}"
echo ""
echo -e "${YELLOW}Remember to open port 443 in your firewall!${NC}"