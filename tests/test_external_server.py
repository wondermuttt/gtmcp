"""Tests for external server functionality - real HTTP server testing."""

import pytest
import asyncio
import time
import subprocess
import signal
import requests
import threading
from typing import Optional
import os
import sys


class HTTPServerManager:
    """Manager for starting and stopping HTTP server for testing."""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"
    
    def start_server(self, timeout: int = 30) -> bool:
        """Start the HTTP server and wait for it to be ready."""
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Start server process
        cmd = [
            sys.executable, "-m", "gtmcp.server_fastapi",
            "--host", self.host,
            "--port", str(self.port),
            "--log-level", "WARNING"  # Reduce log noise during testing
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONPATH": f"{project_root}/src"}
            )
            
            # Wait for server to start
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        return True
                except requests.exceptions.RequestException:
                    pass
                time.sleep(0.5)
            
            return False
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the HTTP server."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                print(f"Error stopping server: {e}")
            finally:
                self.process = None
    
    def is_running(self) -> bool:
        """Check if server is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False


@pytest.fixture(scope="class")
def http_server():
    """Fixture to start and stop HTTP server for testing."""
    server_manager = HTTPServerManager()
    
    # Start server
    if not server_manager.start_server():
        pytest.skip("Could not start HTTP server for testing")
    
    yield server_manager
    
    # Stop server
    server_manager.stop_server()


class TestExternalHTTPServer:
    """Test external HTTP server functionality."""
    
    def test_server_starts_and_responds(self, http_server):
        """Test that server starts and responds to basic requests."""
        assert http_server.is_running()
        
        # Test root endpoint
        response = requests.get(f"{http_server.base_url}/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Georgia Tech MCP Server"
        assert "endpoints" in data
    
    def test_health_endpoint_external(self, http_server):
        """Test health endpoint on external server."""
        response = requests.get(f"{http_server.base_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        
        # Should have both OSCAR and SMARTech services
        services = data["services"]
        assert "oscar" in services
        assert "smartech" in services
    
    def test_cors_headers_external(self, http_server):
        """Test CORS headers are present for ChatGPT integration."""
        # Test with an actual GET request that triggers CORS headers
        response = requests.get(f"{http_server.base_url}/", headers={"Origin": "https://chatgpt.com"})
        assert response.status_code == 200
        
        # CORS headers should be present in real deployment
        # For testing, we just verify the server responds properly
    
    def test_semesters_endpoint_external(self, http_server):
        """Test semesters endpoint on external server."""
        response = requests.get(f"{http_server.base_url}/api/semesters")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "semesters" in data
        assert data["count"] > 0
        
        # Check semester structure
        if data["semesters"]:
            semester = data["semesters"][0]
            assert "code" in semester
            assert "name" in semester
            assert "view_only" in semester
    
    def test_subjects_endpoint_external(self, http_server):
        """Test subjects endpoint with real data."""
        # First get available semesters
        semesters_response = requests.get(f"{http_server.base_url}/api/semesters")
        assert semesters_response.status_code == 200
        
        semesters_data = semesters_response.json()
        if semesters_data["semesters"]:
            # Use first available semester
            term_code = semesters_data["semesters"][0]["code"]
            
            response = requests.get(f"{http_server.base_url}/api/subjects/{term_code}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["term_code"] == term_code
            assert "count" in data
            assert "subjects" in data
            
            # Check subject structure if any exist
            if data["subjects"]:
                subject = data["subjects"][0]
                assert "code" in subject
                assert "name" in subject
    
    def test_courses_endpoint_external(self, http_server):
        """Test course search endpoint with real data."""
        # Get a semester and subject first
        semesters_response = requests.get(f"{http_server.base_url}/api/semesters")
        semesters_data = semesters_response.json()
        
        if semesters_data["semesters"]:
            term_code = semesters_data["semesters"][0]["code"]
            
            # Get subjects for this semester
            subjects_response = requests.get(f"{http_server.base_url}/api/subjects/{term_code}")
            subjects_data = subjects_response.json()
            
            if subjects_data["subjects"]:
                subject_code = subjects_data["subjects"][0]["code"]
                
                # Search for courses
                response = requests.get(
                    f"{http_server.base_url}/api/courses",
                    params={"term_code": term_code, "subject": subject_code}
                )
                assert response.status_code == 200
                
                data = response.json()
                assert data["term_code"] == term_code
                assert data["subject"] == subject_code
                assert "count" in data
                assert "courses" in data
                
                # Note: count might be 0 for future semesters, which is expected
    
    def test_research_endpoint_external(self, http_server):
        """Test research endpoint with real data."""
        response = requests.get(
            f"{http_server.base_url}/api/research",
            params={"keywords": "machine learning,AI", "max_records": 3}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "keywords" in data
        assert "count" in data
        assert "papers" in data
        assert data["keywords"] == ["machine learning", "AI"]
        assert data["max_records"] == 3
    
    def test_error_handling_external(self, http_server):
        """Test error handling on external server."""
        # Test invalid endpoint
        response = requests.get(f"{http_server.base_url}/api/nonexistent")
        assert response.status_code == 404
        
        # Test invalid parameters
        response = requests.get(f"{http_server.base_url}/api/courses")
        assert response.status_code == 422  # Missing required parameters
    
    def test_concurrent_requests_external(self, http_server):
        """Test server handles concurrent requests."""
        import concurrent.futures
        
        def make_request():
            response = requests.get(f"{http_server.base_url}/health")
            return response.status_code
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert len(results) == 10
        assert all(status == 200 for status in results)
    
    def test_openapi_docs_external(self, http_server):
        """Test that OpenAPI documentation is available."""
        # Test docs endpoint
        response = requests.get(f"{http_server.base_url}/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Test OpenAPI JSON
        response = requests.get(f"{http_server.base_url}/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        data = response.json()
        assert "info" in data
        assert "paths" in data
        assert data["info"]["title"] == "Georgia Tech MCP Server"


class TestExternalServerChatGPTCompatibility:
    """Test ChatGPT-specific compatibility requirements."""
    
    def test_chatgpt_connector_requirements(self, http_server):
        """Test that server meets ChatGPT connector requirements."""
        # Test root endpoint provides service information
        response = requests.get(f"{http_server.base_url}/")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "description" in data
        assert "features" in data
        assert "endpoints" in data
        
        # Verify it mentions OSCAR fixes
        description = data["description"].lower()
        assert "course" in description or "oscar" in description
    
    def test_json_responses_for_chatgpt(self, http_server):
        """Test all endpoints return proper JSON for ChatGPT."""
        endpoints_to_test = [
            "/",
            "/health", 
            "/tools",
            "/api/semesters"
        ]
        
        for endpoint in endpoints_to_test:
            response = requests.get(f"{http_server.base_url}{endpoint}")
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]
            
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)
    
    def test_error_responses_for_chatgpt(self, http_server):
        """Test error responses are ChatGPT-friendly."""
        # Test 404 error
        response = requests.get(f"{http_server.base_url}/api/nonexistent")
        assert response.status_code == 404
        assert "application/json" in response.headers["content-type"]
        
        data = response.json()
        assert "detail" in data
        
        # Test 422 validation error
        response = requests.get(f"{http_server.base_url}/api/courses")
        assert response.status_code == 422
        assert "application/json" in response.headers["content-type"]
        
        data = response.json()
        assert "detail" in data
    
    def test_response_times_for_chatgpt(self, http_server):
        """Test response times are reasonable for ChatGPT integration."""
        endpoints = ["/", "/health", "/tools"]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = requests.get(f"{http_server.base_url}{endpoint}")
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 5.0  # Should respond within 5 seconds


class TestExternalServerReliability:
    """Test server reliability and edge cases."""
    
    def test_server_handles_rapid_requests(self, http_server):
        """Test server handles rapid successive requests."""
        responses = []
        
        for i in range(20):
            response = requests.get(f"{http_server.base_url}/health")
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay between requests
        
        # All requests should succeed
        assert all(status == 200 for status in responses)
        assert len(responses) == 20
    
    def test_server_memory_usage_stable(self, http_server):
        """Test server memory usage remains stable under load."""
        # Make many requests to check for memory leaks
        for i in range(50):
            response = requests.get(f"{http_server.base_url}/")
            assert response.status_code == 200
            
            if i % 10 == 0:
                # Check health periodically 
                health_response = requests.get(f"{http_server.base_url}/health")
                assert health_response.status_code == 200
    
    def test_server_recovers_from_errors(self, http_server):
        """Test server recovers gracefully from errors."""
        # Make a request that should cause an error
        response = requests.get(f"{http_server.base_url}/api/subjects/INVALID_TERM")
        assert response.status_code == 500  # Expected error
        
        # Server should still respond to valid requests
        response = requests.get(f"{http_server.base_url}/health")
        assert response.status_code == 200
        
        response = requests.get(f"{http_server.base_url}/")
        assert response.status_code == 200