"""Tests for the base client functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import requests
import aiohttp
from datetime import datetime

from gtmcp.clients.base_client import (
    BaseClient, ClientError, NetworkError, AuthenticationError,
    DataParsingError, RateLimitError, ValidationError
)


class TestBaseClient(BaseClient):
    """Test implementation of BaseClient."""
    
    def test_connection(self) -> bool:
        return True
    
    async def atest_connection(self) -> bool:
        return True


class TestBaseClientInit:
    """Test BaseClient initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        client = TestBaseClient("https://example.com")
        
        assert client.base_url == "https://example.com"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.delay == 1.0
        assert client.user_agent == "GT-MCP-Server/2.0"
        assert client._session is None
        assert client._async_session is None
    
    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        client = TestBaseClient(
            "https://example.com/",
            timeout=60,
            max_retries=5,
            delay=2.0,
            user_agent="Custom-Agent/1.0"
        )
        
        assert client.base_url == "https://example.com"  # Trailing slash removed
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.delay == 2.0
        assert client.user_agent == "Custom-Agent/1.0"


class TestBaseClientContextManagers:
    """Test context manager functionality."""
    
    def test_sync_context_manager(self):
        """Test synchronous context manager."""
        client = TestBaseClient("https://example.com")
        
        with client as c:
            assert c._session is not None
            assert isinstance(c._session, requests.Session)
            assert c._session.headers['User-Agent'] == "GT-MCP-Server/2.0"
        
        assert client._session is None
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test asynchronous context manager."""
        client = TestBaseClient("https://example.com")
        
        async with client as c:
            assert c._async_session is not None
            assert isinstance(c._async_session, aiohttp.ClientSession)
        
        assert client._async_session is None


class TestBaseClientRequests:
    """Test HTTP request functionality."""
    
    @patch('requests.Session.request')
    def test_make_request_success(self, mock_request):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        client = TestBaseClient("https://example.com")
        
        with client:
            response = client._make_request('GET', '/test')
            
        assert response == mock_response
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    def test_make_request_rate_limit_error(self, mock_request):
        """Test request with rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response
        
        client = TestBaseClient("https://example.com")
        
        with client:
            with pytest.raises(RateLimitError):
                client._make_request('GET', '/test')
    
    @patch('requests.Session.request')
    @patch('time.sleep')
    def test_make_request_with_retries(self, mock_sleep, mock_request):
        """Test request with retries on server errors."""
        # First two attempts fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.HTTPError()
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status.return_value = None
        
        mock_request.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        
        client = TestBaseClient("https://example.com")
        
        with client:
            response = client._make_request('GET', '/test')
        
        assert response == mock_response_success
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2  # Two retries
    
    @patch('requests.Session.request')
    @patch('time.sleep')
    def test_make_request_max_retries_exceeded(self, mock_sleep, mock_request):
        """Test request that exceeds max retries."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_request.return_value = mock_response
        
        client = TestBaseClient("https://example.com", max_retries=2)
        
        with client:
            with pytest.raises(NetworkError, match="Server error after 2 attempts"):
                client._make_request('GET', '/test')
        
        assert mock_request.call_count == 2
        assert mock_sleep.call_count == 2
    
    def test_make_request_without_context_manager(self):
        """Test request without context manager raises error."""
        client = TestBaseClient("https://example.com")
        
        with pytest.raises(ClientError, match="Client not initialized"):
            client._make_request('GET', '/test')


class TestBaseClientRateLimiting:
    """Test rate limiting functionality."""
    
    @patch('time.sleep')
    @patch('gtmcp.clients.base_client.datetime')
    def test_rate_limiting_enforced(self, mock_datetime, mock_sleep):
        """Test that rate limiting is enforced."""
        # Mock time progression
        mock_datetime.now.return_value.timestamp.side_effect = [0.0, 0.5, 1.5]
        
        client = TestBaseClient("https://example.com", delay=1.0)
        
        # First call - no sleep
        client._enforce_rate_limit()
        assert not mock_sleep.called
        
        # Second call - should sleep
        client._enforce_rate_limit()
        mock_sleep.assert_called_once_with(0.5)  # 1.0 - 0.5 = 0.5
    
    @patch('asyncio.sleep')
    @patch('gtmcp.clients.base_client.datetime')
    async def test_async_rate_limiting_enforced(self, mock_datetime, mock_sleep):
        """Test that async rate limiting is enforced."""
        # Mock time progression
        mock_datetime.now.return_value.timestamp.side_effect = [0.0, 0.3, 1.3]
        
        client = TestBaseClient("https://example.com", delay=1.0)
        
        # First call - no sleep
        await client._aenforce_rate_limit()
        assert not mock_sleep.called
        
        # Second call - should sleep
        await client._aenforce_rate_limit()
        mock_sleep.assert_called_once_with(0.7)  # 1.0 - 0.3 = 0.7


class TestBaseClientHealthStatus:
    """Test health status functionality."""
    
    def test_get_health_status_healthy(self):
        """Test health status when service is healthy."""
        client = TestBaseClient("https://example.com")
        
        with patch.object(client, 'test_connection', return_value=True):
            status = client.get_health_status()
        
        assert status['service'] == 'TestBaseClient'
        assert status['status'] == 'healthy'
        assert status['base_url'] == 'https://example.com'
        assert 'timestamp' in status
    
    def test_get_health_status_unhealthy(self):
        """Test health status when service is unhealthy."""
        client = TestBaseClient("https://example.com")
        
        with patch.object(client, 'test_connection', return_value=False):
            status = client.get_health_status()
        
        assert status['status'] == 'unhealthy'
    
    def test_get_health_status_error(self):
        """Test health status when connection test raises error."""
        client = TestBaseClient("https://example.com")
        
        with patch.object(client, 'test_connection', side_effect=Exception("Connection failed")):
            status = client.get_health_status()
        
        assert status['status'] == 'error'
        assert status['error'] == 'Connection failed'
    
    @pytest.mark.asyncio
    async def test_aget_health_status_healthy(self):
        """Test async health status when service is healthy."""
        client = TestBaseClient("https://example.com")
        
        with patch.object(client, 'atest_connection', return_value=True):
            status = await client.aget_health_status()
        
        assert status['service'] == 'TestBaseClient'
        assert status['status'] == 'healthy'
        assert status['base_url'] == 'https://example.com'
        assert 'timestamp' in status


class TestBaseClientExceptions:
    """Test custom exception classes."""
    
    def test_client_error_inheritance(self):
        """Test that all custom exceptions inherit from ClientError."""
        assert issubclass(NetworkError, ClientError)
        assert issubclass(AuthenticationError, ClientError)
        assert issubclass(DataParsingError, ClientError)
        assert issubclass(RateLimitError, ClientError)
        assert issubclass(ValidationError, ClientError)
    
    def test_exception_messages(self):
        """Test that exceptions can hold messages."""
        error = NetworkError("Test message")
        assert str(error) == "Test message"