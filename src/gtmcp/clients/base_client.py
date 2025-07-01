"""Base client class with common functionality for all GT system clients."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import aiohttp
import requests
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class ClientError(Exception):
    """Base exception for client errors."""
    pass


class NetworkError(ClientError):
    """Network-related errors."""
    pass


class AuthenticationError(ClientError):
    """Authentication-related errors."""
    pass


class DataParsingError(ClientError):
    """Data parsing-related errors."""
    pass


class RateLimitError(ClientError):
    """Rate limiting errors."""
    pass


class ValidationError(ClientError):
    """Input validation errors."""
    pass


class BaseClient(ABC):
    """Base class for all GT system clients."""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        delay: float = 1.0,
        user_agent: str = "GT-MCP-Server/2.0"
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.user_agent = user_agent
        self._session: Optional[requests.Session] = None
        self._async_session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0.0
        
    def __enter__(self):
        """Context manager entry."""
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': self.user_agent
        })
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._session:
            self._session.close()
            self._session = None
            
    async def __aenter__(self):
        """Async context manager entry."""
        self._async_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={'User-Agent': self.user_agent}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._async_session:
            await self._async_session.close()
            self._async_session = None
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = datetime.now().timestamp()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
            
        self._last_request_time = datetime.now().timestamp()
    
    async def _aenforce_rate_limit(self):
        """Async version of rate limiting."""
        current_time = datetime.now().timestamp()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
            
        self._last_request_time = datetime.now().timestamp()
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> requests.Response:
        """Make HTTP request with retry logic."""
        if not self._session:
            raise ClientError("Client not initialized. Use as context manager.")
            
        full_url = f"{self.base_url}/{url.lstrip('/')}" if not url.startswith('http') else url
        
        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()
                
                logger.debug(f"Making {method} request to {full_url} (attempt {attempt + 1})")
                
                response = self._session.request(
                    method=method,
                    url=full_url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                if response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")
                    
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Request timeout after {self.max_retries} attempts")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Connection error after {self.max_retries} attempts")
                time.sleep(2 ** attempt)
                
            except requests.exceptions.HTTPError as e:
                if response.status_code in [500, 502, 503, 504]:
                    logger.warning(f"Server error on attempt {attempt + 1}: {e}")
                    if attempt == self.max_retries - 1:
                        raise NetworkError(f"Server error after {self.max_retries} attempts")
                    time.sleep(2 ** attempt)
                else:
                    raise NetworkError(f"HTTP error: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise ClientError(f"Request failed after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)
    
    async def _make_async_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make async HTTP request with retry logic."""
        if not self._async_session:
            raise ClientError("Async client not initialized. Use as async context manager.")
            
        full_url = f"{self.base_url}/{url.lstrip('/')}" if not url.startswith('http') else url
        
        for attempt in range(self.max_retries):
            try:
                await self._aenforce_rate_limit()
                
                logger.debug(f"Making async {method} request to {full_url} (attempt {attempt + 1})")
                
                async with self._async_session.request(
                    method=method,
                    url=full_url,
                    **kwargs
                ) as response:
                    
                    if response.status == 429:
                        raise RateLimitError("Rate limit exceeded")
                        
                    response.raise_for_status()
                    return response
                    
            except asyncio.TimeoutError as e:
                logger.warning(f"Async request timeout on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Async request timeout after {self.max_retries} attempts")
                await asyncio.sleep(2 ** attempt)
                
            except aiohttp.ClientConnectionError as e:
                logger.warning(f"Async connection error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Async connection error after {self.max_retries} attempts")
                await asyncio.sleep(2 ** attempt)
                
            except aiohttp.ClientResponseError as e:
                if e.status in [500, 502, 503, 504]:
                    logger.warning(f"Async server error on attempt {attempt + 1}: {e}")
                    if attempt == self.max_retries - 1:
                        raise NetworkError(f"Async server error after {self.max_retries} attempts")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise NetworkError(f"Async HTTP error: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected async error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise ClientError(f"Async request failed after {self.max_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the client can connect to the service."""
        pass
    
    @abstractmethod
    async def atest_connection(self) -> bool:
        """Async version of connection test."""
        pass
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the service."""
        try:
            success = self.test_connection()
            return {
                'service': self.__class__.__name__,
                'status': 'healthy' if success else 'unhealthy',
                'base_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'service': self.__class__.__name__,
                'status': 'error',
                'error': str(e),
                'base_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }
    
    async def aget_health_status(self) -> Dict[str, Any]:
        """Async version of health status check."""
        try:
            success = await self.atest_connection()
            return {
                'service': self.__class__.__name__,
                'status': 'healthy' if success else 'unhealthy',
                'base_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'service': self.__class__.__name__,
                'status': 'error',
                'error': str(e),
                'base_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }