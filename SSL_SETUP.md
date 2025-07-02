# SSL/HTTPS Setup for Georgia Tech MCP Server

This guide provides complete instructions for setting up SSL/HTTPS for the Georgia Tech MCP Server using Let's Encrypt certificates.

## Quick Setup

1. **Run the SSL setup script (requires sudo):**
   ```bash
   sudo ./setup_ssl.sh
   ```

2. **Start the server with SSL:**
   ```bash
   ./start_server_ssl.sh
   ```

3. **Access your server:**
   - Direct HTTPS: `https://wmjump1.henkelman.net:8080`
   - Via nginx proxy: `https://wmjump1.henkelman.net` (if nginx is configured)

## What the Setup Script Does

The `setup_ssl.sh` script automatically:

1. **Installs Let's Encrypt certbot** (if not already installed)
2. **Obtains SSL certificates** for wmjump1.henkelman.net
3. **Creates certificate symlinks** in `/home/phenkelm/src/gtmcp/certs/`
4. **Sets up automatic renewal** (runs twice daily)
5. **Configures nginx** as a reverse proxy (optional, if nginx is installed)
6. **Updates application configuration** to use SSL

## Manual SSL Configuration

If you prefer to configure SSL manually:

### 1. Obtain Certificates

```bash
# Install certbot
sudo apt-get update
sudo apt-get install -y certbot

# Obtain certificate (standalone method)
sudo certbot certonly --standalone -d wmjump1.henkelman.net

# Or with nginx (if running)
sudo certbot certonly --nginx -d wmjump1.henkelman.net
```

### 2. Update Configuration

Edit `config.json`:

```json
{
  "server": {
    "ssl_enabled": true,
    "ssl_certfile": "/home/phenkelm/src/gtmcp/certs/fullchain.pem",
    "ssl_keyfile": "/home/phenkelm/src/gtmcp/certs/privkey.pem",
    "external_host": "wmjump1.henkelman.net",
    "external_port": 443,
    "external_scheme": "https"
  }
}
```

### 3. Create Certificate Links

```bash
sudo mkdir -p /home/phenkelm/src/gtmcp/certs
sudo ln -sf /etc/letsencrypt/live/wmjump1.henkelman.net/fullchain.pem /home/phenkelm/src/gtmcp/certs/
sudo ln -sf /etc/letsencrypt/live/wmjump1.henkelman.net/privkey.pem /home/phenkelm/src/gtmcp/certs/
```

## Running the Server

### Option 1: Direct HTTPS (Port 8080)

```bash
./start_server_ssl.sh
```

The server will be available at: `https://wmjump1.henkelman.net:8080`

### Option 2: Via nginx Proxy (Port 443)

If nginx is configured by the setup script, the server will be accessible at:
`https://wmjump1.henkelman.net`

### Option 3: As a System Service

```bash
# Copy service file
sudo cp gtmcp-ssl.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable gtmcp-ssl
sudo systemctl start gtmcp-ssl

# Check status
sudo systemctl status gtmcp-ssl
```

## Certificate Renewal

Certificates are automatically renewed by the systemd timer created during setup:

```bash
# Check renewal timer
sudo systemctl status certbot-renewal.timer

# Manually test renewal
sudo certbot renew --dry-run

# Force renewal (if needed)
sudo certbot renew --force-renewal
```

## Nginx Configuration

If nginx is installed, the setup script creates a configuration at `/etc/nginx/sites-available/gtmcp`:

- HTTP (port 80) redirects to HTTPS
- HTTPS (port 443) proxies to the FastAPI server on port 8080
- Modern SSL configuration with TLS 1.2/1.3
- HSTS header for security

## ChatGPT Integration

After SSL setup, update your ChatGPT configuration:

1. In ChatGPT settings, update your custom tool URL to:
   - `https://wmjump1.henkelman.net` (if using nginx)
   - `https://wmjump1.henkelman.net:8080` (if using direct HTTPS)

2. The server provides the AI plugin manifest at:
   `https://wmjump1.henkelman.net/.well-known/ai-plugin.json`

## Troubleshooting

### Certificate Not Found
```bash
# Check certificate location
sudo ls -la /etc/letsencrypt/live/wmjump1.henkelman.net/

# Check symlinks
ls -la /home/phenkelm/src/gtmcp/certs/
```

### Port Already in Use
```bash
# Check what's using port 80/443
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting services
sudo systemctl stop apache2  # if Apache is running
```

### Permission Denied
```bash
# Fix certificate permissions
sudo chown -R phenkelm:phenkelm /home/phenkelm/src/gtmcp/certs/
```

### SSL Handshake Failed
```bash
# Test SSL configuration
openssl s_client -connect wmjump1.henkelman.net:443 -servername wmjump1.henkelman.net

# Check nginx configuration
sudo nginx -t
```

## Security Considerations

1. **Firewall**: Ensure ports 80 and 443 are open:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8080/tcp  # if using direct HTTPS
   ```

2. **Certificate Security**: 
   - Private keys are only readable by root and linked for the application
   - Certificates auto-renew to prevent expiration

3. **HTTPS Headers**: The nginx configuration includes:
   - HSTS (HTTP Strict Transport Security)
   - Modern TLS protocols only
   - Secure cipher suites

## Additional Options

### Custom Certificate Path
```bash
./start_server_ssl.sh 0.0.0.0 8080 /path/to/cert.pem /path/to/key.pem
```

### Development with Self-Signed Certificates
For development/testing only:
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Run server with self-signed cert
./start_server_ssl.sh 0.0.0.0 8080 cert.pem key.pem
```

**Note**: Self-signed certificates will show security warnings in browsers and won't work with ChatGPT.