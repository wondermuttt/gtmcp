# Georgia Tech MCP Server - Linux Deployment Guide

This guide walks you through deploying the GT MCP Server on a Linux server.

## Prerequisites

- Linux server with internet access
- Python 3.11+ available
- Git installed
- Anaconda or Miniconda installed (recommended)

## Step 1: Install Anaconda (if not already installed)

```bash
# Download Miniconda (lightweight option)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Make executable and run installer
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh

# Follow the installer prompts, then reload shell
source ~/.bashrc
```

## Step 2: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/wondermuttt/gtmcp.git

# Navigate to project directory
cd gtmcp
```

## Step 3: Automated Setup

The project includes an automated setup script:

```bash
# Make setup script executable
chmod +x setup.sh

# Run the setup script (creates environment and installs dependencies)
./setup.sh
```

The setup script will:
- Create a conda environment named `gtmcp` with Python 3.11
- Install all required dependencies
- Install the package in development mode
- Display next steps

## Step 4: Manual Setup (Alternative)

If you prefer manual setup or the script fails:

```bash
# Create conda environment
conda create -n gtmcp python=3.11 -y

# Activate environment
conda activate gtmcp

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

## Step 5: Configuration

### Basic Configuration
The server comes with sensible defaults in `config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080,
    "log_level": "INFO"
  },
  "scraper": {
    "delay": 1.0,
    "timeout": 30,
    "max_retries": 3
  },
  "cache": {
    "enabled": true,
    "ttl_seconds": 3600
  }
}
```

### Custom Configuration
Create a custom config file if needed:

```bash
# Copy default config
cp config.json config.local.json

# Edit as needed
nano config.local.json
```

## Step 6: Test the Installation

```bash
# Activate environment
conda activate gtmcp

# Run integration test
python test_server.py

# Run unit tests
python -m pytest tests/ -v
```

Expected output:
```
✅ All scraper tests completed successfully!
69 passed in X.XXs
```

## Step 7: Run the Server

### Quick Start
```bash
# Using the startup script (recommended)
./start_server.sh
```

### Manual Start
```bash
# Activate environment
conda activate gtmcp

# Run server with default config
python -m gtmcp.server

# Or with custom config
python -m gtmcp.server --config config.local.json

# Or with command line overrides
python -m gtmcp.server --host 127.0.0.1 --port 9000 --log-level DEBUG
```

## Step 8: Verify Server is Running

The server will start and display:
```
Starting Georgia Tech MCP Server on 0.0.0.0:8080
Scraper configured with 1.0s delay
```

## Production Deployment Options

### Option 1: systemd Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/gtmcp.service
```

```ini
[Unit]
Description=Georgia Tech MCP Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/gtmcp
ExecStart=/home/your-username/anaconda3/envs/gtmcp/bin/python -m gtmcp.server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable gtmcp
sudo systemctl start gtmcp
sudo systemctl status gtmcp
```

### Option 2: Docker (if preferred)

Create a Dockerfile:
```dockerfile
FROM continuumio/miniconda3

WORKDIR /app
COPY . .

RUN conda env create -f environment.yml
RUN echo "conda activate gtmcp" >> ~/.bashrc

EXPOSE 8080

CMD ["conda", "run", "-n", "gtmcp", "python", "-m", "gtmcp.server"]
```

### Option 3: Screen/tmux Session

For simple deployment:
```bash
# Using screen
screen -S gtmcp
conda activate gtmcp
./start_server.sh
# Press Ctrl+A, D to detach

# Using tmux
tmux new-session -s gtmcp
conda activate gtmcp
./start_server.sh
# Press Ctrl+B, D to detach
```

## Firewall Configuration

If using a firewall, allow the port:

```bash
# UFW (Ubuntu)
sudo ufw allow 8080

# iptables
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

# firewalld (RHEL/CentOS)
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

## Monitoring and Logs

### View Logs
```bash
# If running via systemd
sudo journalctl -u gtmcp -f

# If running manually, logs go to stdout
# Configure log files in your config if needed
```

### Health Check
```bash
# Test if server is responding (replace with your server IP)
curl http://localhost:8080/health

# Or use the MCP client tools to test functionality
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Change port in config.json or use command line
   python -m gtmcp.server --port 8081
   ```

2. **Permission denied**
   ```bash
   # Make scripts executable
   chmod +x setup.sh start_server.sh
   ```

3. **Conda environment not found**
   ```bash
   # Ensure conda is in PATH
   source ~/anaconda3/etc/profile.d/conda.sh
   conda activate gtmcp
   ```

4. **Network connectivity issues**
   ```bash
   # Test GT OSCAR access
   curl -I https://oscar.gatech.edu/pls/bprod/bwckschd.p_disp_dyn_sched
   ```

### Logs and Debugging

Enable debug logging:
```bash
python -m gtmcp.server --log-level DEBUG
```

Run tests to verify functionality:
```bash
python test_server.py
python -m pytest tests/ -v
```

## Security Considerations

1. **Firewall**: Only open necessary ports
2. **User permissions**: Run as non-root user
3. **Rate limiting**: Respect GT's servers (built-in 1-second delays)
4. **Updates**: Regularly update dependencies
5. **Monitoring**: Monitor for errors and performance

## Performance Tuning

1. **Caching**: Enable caching in config.json (default: enabled)
2. **Delays**: Adjust scraper delay based on usage patterns
3. **Timeouts**: Tune request timeouts for your network
4. **Resources**: Monitor CPU and memory usage

For questions or issues, refer to the project README.md or create an issue on GitHub.