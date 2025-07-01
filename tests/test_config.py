"""Tests for configuration management."""

import json
import os
import tempfile
import pytest

from gtmcp.config import Config, ServerConfig, ScraperConfig, CacheConfig, load_config


class TestServerConfig:
    """Tests for ServerConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.log_level == "INFO"
        
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ServerConfig(host="127.0.0.1", port=9000, log_level="DEBUG")
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.log_level == "DEBUG"
        
    def test_port_validation(self):
        """Test port validation."""
        # Valid ports should work
        ServerConfig(port=1)
        ServerConfig(port=65535)
        
        # Note: Pydantic doesn't enforce port range validation by default
        # This test is for documentation purposes
        # In production, additional validation could be added
    
    def test_ssl_configuration(self):
        """Test SSL configuration settings."""
        config = ServerConfig(
            ssl_enabled=True,
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem",
            ssl_ca_certs="/path/to/ca.pem"
        )
        assert config.ssl_enabled is True
        assert config.ssl_certfile == "/path/to/cert.pem"
        assert config.ssl_keyfile == "/path/to/key.pem"
        assert config.ssl_ca_certs == "/path/to/ca.pem"
        
    def test_ssl_defaults(self):
        """Test SSL default configuration."""
        config = ServerConfig()
        assert config.ssl_enabled is False
        assert config.ssl_certfile is None
        assert config.ssl_keyfile is None
        assert config.ssl_ca_certs is None
        
    def test_external_url_configuration(self):
        """Test external URL configuration settings."""
        config = ServerConfig(
            external_host="wmjump1.henkelman.net",
            external_port=8080,
            external_scheme="https"
        )
        assert config.external_host == "wmjump1.henkelman.net"
        assert config.external_port == 8080
        assert config.external_scheme == "https"
        
    def test_external_url_defaults(self):
        """Test external URL default configuration."""
        config = ServerConfig()
        assert config.external_host is None
        assert config.external_port is None
        assert config.external_scheme == "http"
        
    def test_get_external_base_url(self):
        """Test external base URL generation."""
        # Test with external configuration
        config = ServerConfig(
            host="0.0.0.0",
            port=8080,
            external_host="wmjump1.henkelman.net",
            external_port=8080,
            external_scheme="https"
        )
        assert config.get_external_base_url() == "https://wmjump1.henkelman.net:8080"
        
        # Test without external configuration (fallback to server config)
        config = ServerConfig(host="localhost", port=9000)
        assert config.get_external_base_url() == "http://localhost:9000"
        
        # Test with external host but default port
        config = ServerConfig(
            external_host="example.com",
            external_scheme="https"
        )
        # Should use server port as fallback
        assert config.get_external_base_url() == "https://example.com:8080"


class TestScraperConfig:
    """Tests for ScraperConfig model."""
    
    def test_default_values(self):
        """Test default scraper configuration."""
        config = ScraperConfig()
        assert config.delay == 1.0
        assert config.timeout == 30
        assert config.max_retries == 3
        
    def test_custom_values(self):
        """Test custom scraper configuration."""
        config = ScraperConfig(delay=0.5, timeout=60, max_retries=5)
        assert config.delay == 0.5
        assert config.timeout == 60
        assert config.max_retries == 5
        
    def test_validation(self):
        """Test scraper config validation."""
        # Note: Pydantic doesn't enforce these validations by default
        # Validation is handled in the GTOscarScraper constructor
        # This test is for documentation purposes
        ScraperConfig(delay=0.0)  # This should work
        ScraperConfig(timeout=1)  # This should work
        ScraperConfig(max_retries=1)  # This should work


class TestCacheConfig:
    """Tests for CacheConfig model."""
    
    def test_default_values(self):
        """Test default cache configuration."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.ttl_seconds == 3600
        
    def test_custom_values(self):
        """Test custom cache configuration."""
        config = CacheConfig(enabled=False, ttl_seconds=7200)
        assert config.enabled is False
        assert config.ttl_seconds == 7200


class TestConfig:
    """Tests for main Config model."""
    
    def test_default_config(self):
        """Test default main configuration."""
        config = Config()
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.scraper, ScraperConfig)
        assert isinstance(config.cache, CacheConfig)
        
        # Test default values are present
        assert config.server.host == "0.0.0.0"
        assert config.scraper.delay == 1.0
        assert config.cache.enabled is True
        
    def test_custom_config(self):
        """Test custom main configuration."""
        config = Config(
            server=ServerConfig(host="127.0.0.1", port=9000),
            scraper=ScraperConfig(delay=0.5),
            cache=CacheConfig(enabled=False)
        )
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.scraper.delay == 0.5
        assert config.cache.enabled is False


class TestLoadConfig:
    """Tests for configuration loading."""
    
    def test_load_default_config(self):
        """Test loading default configuration when no file exists."""
        # Test with non-existent file
        config = load_config("/non/existent/path.json")
        assert isinstance(config, Config)
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8080
        
    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        config_data = {
            "server": {
                "host": "127.0.0.1",
                "port": 9000,
                "log_level": "DEBUG",
                "ssl_enabled": True,
                "ssl_certfile": "/etc/ssl/cert.pem",
                "ssl_keyfile": "/etc/ssl/key.pem",
                "external_host": "example.com",
                "external_port": 443,
                "external_scheme": "https"
            },
            "scraper": {
                "delay": 0.5,
                "timeout": 60,
                "max_retries": 5
            },
            "cache": {
                "enabled": False,
                "ttl_seconds": 7200
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
            
        try:
            config = load_config(temp_path)
            assert config.server.host == "127.0.0.1"
            assert config.server.port == 9000
            assert config.server.log_level == "DEBUG"
            assert config.server.ssl_enabled is True
            assert config.server.ssl_certfile == "/etc/ssl/cert.pem"
            assert config.server.ssl_keyfile == "/etc/ssl/key.pem"
            assert config.server.external_host == "example.com"
            assert config.server.external_port == 443
            assert config.server.external_scheme == "https"
            assert config.scraper.delay == 0.5
            assert config.scraper.timeout == 60
            assert config.scraper.max_retries == 5
            assert config.cache.enabled is False
            assert config.cache.ttl_seconds == 7200
        finally:
            os.unlink(temp_path)
            
    def test_load_config_invalid_json(self):
        """Test loading configuration with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
            
        try:
            # Should fall back to default config
            config = load_config(temp_path)
            assert isinstance(config, Config)
            assert config.server.host == "0.0.0.0"  # Default values
        finally:
            os.unlink(temp_path)
            
    def test_load_config_partial_data(self):
        """Test loading configuration with partial data."""
        config_data = {
            "server": {
                "host": "127.0.0.1"
                # Missing port and log_level
            }
            # Missing scraper and cache sections
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
            
        try:
            config = load_config(temp_path)
            assert config.server.host == "127.0.0.1"  # From file
            assert config.server.port == 8080  # Default value
            assert config.scraper.delay == 1.0  # Default value
            assert config.cache.enabled is True  # Default value
        finally:
            os.unlink(temp_path)
            
    def test_load_config_from_current_directory(self, monkeypatch):
        """Test loading config.json from current directory."""
        config_data = {
            "server": {"host": "test.example.com"}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
                
            # Change to temp directory
            monkeypatch.chdir(temp_dir)
            
            config = load_config()
            assert config.server.host == "test.example.com"