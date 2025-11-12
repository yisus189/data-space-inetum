"""
Unit tests for error handling middleware.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from src.app.middleware.errors import ErrorHandlerMiddleware, RequestLoggingMiddleware, create_error_handlers


@pytest.fixture
def app():
    """Create test FastAPI app with middleware."""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add error handlers
    create_error_handlers(app)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    @app.get("/error/http")
    def http_error():
        raise HTTPException(status_code=404, detail="Not found")
    
    @app.get("/error/exception")
    def exception_error():
        raise ValueError("Something went wrong")
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestErrorHandlerMiddleware:
    """Tests for ErrorHandlerMiddleware."""
    
    def test_successful_request(self, client):
        """Test successful request returns normal response."""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "X-Request-ID" in response.headers
    
    def test_http_exception_handling(self, client):
        """Test HTTPException is caught and formatted."""
        response = client.get("/error/http")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "http_404"
        assert data["error"]["message"] == "Not found"
        assert "request_id" in data["error"]
        assert "X-Request-ID" in response.headers
    
    def test_generic_exception_handling(self, client):
        """Test generic exceptions are caught and return 500."""
        response = client.get("/error/exception")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "internal_server_error"
        assert "internal server error" in data["error"]["message"].lower()
        assert "request_id" in data["error"]
        assert "X-Request-ID" in response.headers
    
    def test_request_id_propagation(self, client):
        """Test request ID is propagated from header."""
        custom_request_id = "custom-id-12345"
        response = client.get("/test", headers={"X-Request-ID": custom_request_id})
        
        assert response.headers["X-Request-ID"] == custom_request_id
    
    def test_request_id_generation(self, client):
        """Test request ID is generated if not provided."""
        response1 = client.get("/test")
        response2 = client.get("/test")
        
        request_id_1 = response1.headers["X-Request-ID"]
        request_id_2 = response2.headers["X-Request-ID"]
        
        assert request_id_1 != request_id_2
        assert len(request_id_1) > 0
        assert len(request_id_2) > 0


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""
    
    def test_logging_middleware_doesnt_break_requests(self, client):
        """Test logging middleware doesn't interfere with normal operation."""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
