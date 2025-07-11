"""Configuration management for Georgia Tech MCP Server."""

import json
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8080, description="Port to bind to") 
    log_level: str = Field(default="INFO", description="Log level")
    
    # SSL/HTTPS Configuration
    ssl_enabled: bool = Field(default=False, description="Enable SSL/HTTPS")
    ssl_certfile: Optional[str] = Field(default=None, description="Path to SSL certificate file")
    ssl_keyfile: Optional[str] = Field(default=None, description="Path to SSL private key file")
    ssl_ca_certs: Optional[str] = Field(default=None, description="Path to CA certificates file")
    
    # External URL Configuration (for ChatGPT manifests)
    external_host: Optional[str] = Field(default=None, description="External hostname for API manifests")
    external_port: Optional[int] = Field(default=None, description="External port for API manifests")
    external_scheme: str = Field(default="http", description="External URL scheme (http/https)")
    
    def get_external_base_url(self) -> str:
        """Get the external base URL for API manifests."""
        host = self.external_host or ("localhost" if self.host == "0.0.0.0" else self.host)
        port = self.external_port or self.port
        scheme = self.external_scheme
        
        # Don't include port for standard ports
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            return f"{scheme}://{host}"
        else:
            return f"{scheme}://{host}:{port}"


class ScraperConfig(BaseModel):
    """Scraper configuration."""
    delay: float = Field(default=1.0, description="Delay between requests in seconds")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")


class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = Field(default=True, description="Enable caching")
    ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")


class Config(BaseModel):
    """Main configuration."""
    server: ServerConfig = Field(default_factory=ServerConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or use defaults."""
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return Config(**config_data)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            print("Using default configuration")
    
    # Try to load from default locations
    default_paths = [
        "config.json",
        "gtmcp.json",
        os.path.expanduser("~/.gtmcp/config.json"),
        "/etc/gtmcp/config.json"
    ]
    
    for path in default_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config_data = json.load(f)
                print(f"Loaded configuration from: {path}")
                return Config(**config_data)
            except Exception as e:
                print(f"Warning: Could not load config from {path}: {e}")
                continue
    
    print("Using default configuration")
    return Config()