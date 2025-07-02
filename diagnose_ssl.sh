#!/bin/bash

# SSL Diagnostics Script for Georgia Tech MCP Server
# This script helps diagnose SSL certificate issues

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DOMAIN="wmjump1.henkelman.net"

echo -e "${BLUE}SSL Certificate Diagnostics for ${DOMAIN}${NC}"
echo "==========================================="

# 1. Check DNS Resolution
echo -e "\n${YELLOW}1. DNS Resolution Check:${NC}"
echo -n "Server Public IP: "
curl -s ifconfig.me || curl -s icanhazip.com || echo "Could not determine"
echo -n "Domain resolves to: "
dig +short ${DOMAIN} | tail -n1 || echo "DNS lookup failed"

# 2. Check Port Availability
echo -e "\n${YELLOW}2. Port Availability:${NC}"
echo "Port 80 (HTTP):"
if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
    lsof -Pi :80 -sTCP:LISTEN 2>/dev/null || echo "Port 80 is in use (details unavailable)"
else
    echo -e "${GREEN}Port 80 is available${NC}"
fi

echo -e "\nPort 443 (HTTPS):"
if lsof -Pi :443 -sTCP:LISTEN -t >/dev/null 2>&1; then
    lsof -Pi :443 -sTCP:LISTEN 2>/dev/null || echo "Port 443 is in use (details unavailable)"
else
    echo -e "${GREEN}Port 443 is available${NC}"
fi

# 3. Check Certbot Status
echo -e "\n${YELLOW}3. Certbot Status:${NC}"
if command -v certbot >/dev/null 2>&1; then
    echo "Certbot version:"
    certbot --version
    echo -e "\nExisting certificates:"
    certbot certificates 2>/dev/null || echo "Unable to list certificates (may need sudo)"
else
    echo -e "${RED}Certbot is not installed${NC}"
fi

# 4. Check Let's Encrypt Directories
echo -e "\n${YELLOW}4. Let's Encrypt Directories:${NC}"
if [ -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
    echo -e "${GREEN}Certificate directory exists${NC}"
    echo "Contents:"
    ls -la "/etc/letsencrypt/live/${DOMAIN}/" 2>/dev/null || echo "Unable to list (may need sudo)"
else
    echo -e "${RED}Certificate directory does not exist${NC}"
fi

# 5. Check Application Certificate Links
echo -e "\n${YELLOW}5. Application Certificate Links:${NC}"
APP_CERT_DIR="/home/phenkelm/src/gtmcp/certs"
if [ -d "$APP_CERT_DIR" ]; then
    echo "Application cert directory exists"
    echo "Contents:"
    ls -la "$APP_CERT_DIR/"
else
    echo -e "${RED}Application cert directory does not exist${NC}"
fi

# 6. Test HTTP Connectivity
echo -e "\n${YELLOW}6. HTTP Connectivity Test:${NC}"
echo "Testing HTTP connection to ${DOMAIN}..."
curl -I -m 5 "http://${DOMAIN}" 2>/dev/null | head -n 1 || echo "HTTP connection failed"

# 7. Check Firewall Rules
echo -e "\n${YELLOW}7. Firewall Status:${NC}"
if command -v ufw >/dev/null 2>&1; then
    ufw status | grep -E "(80|443)" || echo "No HTTP/HTTPS rules found in UFW"
else
    echo "UFW not installed"
fi

if command -v iptables >/dev/null 2>&1; then
    echo -e "\nIPTables rules for ports 80/443:"
    iptables -L -n | grep -E "(80|443)" 2>/dev/null || echo "No relevant iptables rules or insufficient permissions"
fi

# 8. Recent Let's Encrypt Logs
echo -e "\n${YELLOW}8. Recent Let's Encrypt Logs:${NC}"
if [ -f "/var/log/letsencrypt/letsencrypt.log" ]; then
    echo "Last 20 lines of Let's Encrypt log:"
    tail -n 20 /var/log/letsencrypt/letsencrypt.log 2>/dev/null || echo "Unable to read logs (may need sudo)"
else
    echo "Let's Encrypt log file not found"
fi

# 9. Recommendations
echo -e "\n${YELLOW}9. Recommendations:${NC}"
echo "If certificate generation is failing:"
echo "1. Ensure DNS is properly configured and propagated"
echo "2. Make sure ports 80 and 443 are open in firewall"
echo "3. Stop any services using port 80 during certificate generation"
echo "4. Try the improved setup script: sudo ./setup_ssl_v2.sh"
echo "5. Check Let's Encrypt rate limits: https://letsencrypt.org/docs/rate-limits/"

echo -e "\n${BLUE}Diagnostic complete!${NC}"