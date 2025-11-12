"""Unit tests for error handling middleware."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from src.app.middleware.errors import (
    ErrorHandlingMiddleware,
    http_exception_handler,
    validation_exception_handler,
    _get_error_code
)


@pytest.fixture
def app():
    """Create test FastAPI app with error middleware."""
    app = FastAPI()
    
    # Register exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Add middleware
    app.add_middleware(ErrorHandlingMiddleware)
    
    @app.get("/success")
    def success():
        return {"message": "success"}
    
    @app.get("/http-error")
    def http_error():
        raise HTTPException(status_code=404, detail="Resource not found")
    
    @app.get("/unhandled-error")
    def unhandled_error():
        raise ValueError("Something went wrong")
    
    @app.get("/auth-error")
    def auth_error():
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    class Item(BaseModel):
        name: str
        value: int
    
    @app.post("/validate")
    def validate(item: Item):
        return item
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_success_request(client):
    """Test successful request doesn't trigger error handling."""
    response = client.get("/success")
    assert response.status_code == 200
    assert response.json() == {"message": "success"}
    assert "X-Request-ID" in response.headers


def test_http_exception_404(client):
    """Test HTTPException is converted to standardized error response."""
    response = client.get("/http-error")
    assert response.status_code == 404
    
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"
    assert data["error"]["message"] == "Resource not found"
    assert "request_id" in data["error"]
    assert "X-Request-ID" in response.headers


def test_http_exception_401(client):
    """Test 401 HTTPException."""
    response = client.get("/auth-error")
    assert response.status_code == 401
    
    data = response.json()
    assert data["error"]["code"] == "unauthorized"
    assert data["error"]["message"] == "Invalid credentials"


def test_unhandled_exception(client):
    """Test unhandled exception returns 500."""
    response = client.get("/unhandled-error")
    assert response.status_code == 500
    
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "internal_server_error"
    assert data["error"]["message"] == "An internal error occurred"
    assert "request_id" in data["error"]


def test_validation_error(client):
    """Test validation error returns 422."""
    response = client.post("/validate", json={"name": "test"})  # Missing 'value'
    assert response.status_code == 422
    
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"
    assert data["error"]["message"] == "Request validation failed"
    assert "details" in data["error"]


def test_request_id_in_headers(client):
    """Test that request_id is added to all responses."""
    # Success response
    response = client.get("/success")
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    
    # Error response
    response = client.get("/http-error")
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None


def test_error_code_mapping():
    """Test various HTTP status codes map to correct error codes."""
    assert _get_error_code(400) == "bad_request"
    assert _get_error_code(401) == "unauthorized"
    assert _get_error_code(403) == "forbidden"
    assert _get_error_code(404) == "not_found"
    assert _get_error_code(422) == "validation_error"
    assert _get_error_code(500) == "internal_server_error"
    assert _get_error_code(503) == "service_unavailable"
    assert _get_error_code(999) == "http_999"  # Unknown status
