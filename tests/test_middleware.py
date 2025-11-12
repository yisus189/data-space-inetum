"""
Unit tests for error handling middleware.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from src.app.middleware.errors import ErrorHandlerMiddleware


@pytest.fixture
def app():
    """Create test FastAPI app with error middleware."""
    test_app = FastAPI()
    test_app.add_middleware(ErrorHandlerMiddleware)
    
    @test_app.get("/success")
    def success_endpoint():
        return {"status": "ok"}
    
    @test_app.get("/http-error")
    def http_error_endpoint():
        raise HTTPException(status_code=404, detail="Not found")
    
    @test_app.get("/server-error")
    def server_error_endpoint():
        raise Exception("Unexpected error")
    
    @test_app.get("/validation-error")
    def validation_error_endpoint(param: int):
        return {"param": param}
    
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestErrorHandlerMiddleware:
    """Tests for error handler middleware."""
    
    def test_success_response_includes_request_id(self, client):
        """Test that successful responses include request ID header."""
        response = client.get("/success")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert response.json() == {"status": "ok"}
    
    def test_http_exception_formatted_correctly(self, client):
        """Test that HTTPException is formatted as structured JSON."""
        response = client.get("/http-error")
        
        assert response.status_code == 404
        assert "X-Request-ID" in response.headers
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "http_404"
        assert data["error"]["message"] == "Not found"
        assert "request_id" in data["error"]
    
    def test_server_error_formatted_correctly(self, client):
        """Test that unhandled exceptions are formatted as structured JSON."""
        response = client.get("/server-error")
        
        assert response.status_code == 500
        assert "X-Request-ID" in response.headers
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "internal_server_error"
        assert data["error"]["message"] == "An unexpected error occurred"
        assert "request_id" in data["error"]
    
    def test_validation_error_formatted_correctly(self, client):
        """Test that validation errors are formatted correctly."""
        # Send invalid query parameter (string instead of int)
        response = client.get("/validation-error?param=not-a-number")
        
        assert response.status_code == 422
        assert "X-Request-ID" in response.headers
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "validation_error"
        assert data["error"]["message"] == "Request validation failed"
        assert "details" in data["error"]
        assert "request_id" in data["error"]
    
    def test_request_id_is_unique(self, client):
        """Test that each request gets a unique request ID."""
        response1 = client.get("/success")
        response2 = client.get("/success")
        
        request_id1 = response1.headers["X-Request-ID"]
        request_id2 = response2.headers["X-Request-ID"]
        
        assert request_id1 != request_id2
