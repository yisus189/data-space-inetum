"""Tests for authentication and authorization."""
import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from src.auth.keycloak import decode_token, extract_roles, extract_username, jwks_cache
from src.app.deps import current_user, require_provider, require_consumer, require_broker, User
from src.config import settings
from tests.test_utils import create_test_jwt, create_test_jwks


class TestTokenValidation:
    """Tests for JWT token validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear JWKS cache before each test
        jwks_cache.clear()
        
        # Mock the JWKS endpoint
        self.test_jwks = create_test_jwks()
        
        # Patch requests.get to return test JWKS
        self.patcher = patch('src.auth.keycloak.requests.get')
        self.mock_get = self.patcher.start()
        
        mock_response = MagicMock()
        mock_response.json.return_value = self.test_jwks
        mock_response.raise_for_status = MagicMock()
        self.mock_get.return_value = mock_response
    
    def teardown_method(self):
        """Clean up after tests."""
        self.patcher.stop()
        jwks_cache.clear()
    
    def test_valid_token_decoding(self):
        """Test that a valid token is correctly decoded."""
        token = create_test_jwt(
            username="alice",
            roles=["provider", "consumer"]
        )
        
        payload = decode_token(token)
        
        assert payload["preferred_username"] == "alice"
        assert "provider" in payload["realm_access"]["roles"]
        assert "consumer" in payload["realm_access"]["roles"]
    
    def test_expired_token(self):
        """Test that an expired token raises an exception."""
        token = create_test_jwt(
            username="bob",
            roles=["provider"],
            exp_delta=-3600  # Expired 1 hour ago
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_invalid_signature(self):
        """Test that a token with invalid signature is rejected."""
        # Create a valid token
        token = create_test_jwt(username="eve", roles=["consumer"])
        
        # Tamper with the token (change last character)
        tampered_token = token[:-5] + "XXXXX"
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered_token)
        
        assert exc_info.value.status_code == 401
    
    def test_invalid_issuer(self):
        """Test that a token with wrong issuer is rejected."""
        token = create_test_jwt(
            username="mallory",
            roles=["broker"],
            issuer="http://wrong-issuer.com"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        
        assert exc_info.value.status_code == 401
        assert "claims" in exc_info.value.detail.lower() or "validation" in exc_info.value.detail.lower()
    
    def test_invalid_audience(self):
        """Test that a token with wrong audience is rejected when audience is configured."""
        # Set audience requirement
        original_audience = settings.KEYCLOAK_AUDIENCE
        settings.KEYCLOAK_AUDIENCE = "expected-audience"
        
        try:
            token = create_test_jwt(
                username="trudy",
                roles=["provider"],
                audience="wrong-audience"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                decode_token(token)
            
            assert exc_info.value.status_code == 401
        finally:
            settings.KEYCLOAK_AUDIENCE = original_audience
    
    def test_extract_roles(self):
        """Test role extraction from token payload."""
        payload = {
            "realm_access": {
                "roles": ["provider", "consumer", "broker"]
            }
        }
        
        roles = extract_roles(payload)
        
        assert len(roles) == 3
        assert "provider" in roles
        assert "consumer" in roles
        assert "broker" in roles
    
    def test_extract_roles_empty(self):
        """Test role extraction when no roles are present."""
        payload = {}
        roles = extract_roles(payload)
        assert roles == []
    
    def test_extract_username(self):
        """Test username extraction from token payload."""
        payload = {"preferred_username": "alice"}
        username = extract_username(payload)
        assert username == "alice"
    
    def test_extract_username_fallback(self):
        """Test username extraction falls back to sub when preferred_username is missing."""
        payload = {"sub": "user-123"}
        username = extract_username(payload)
        assert username == "user-123"


class TestRoleBasedAuthorization:
    """Tests for role-based authorization guards."""
    
    def test_require_provider_with_provider_role(self):
        """Test that require_provider allows users with provider role."""
        user = User(username="alice", roles=["provider"], token_payload={})
        result = require_provider(user)
        assert result == user
    
    def test_require_provider_with_broker_role(self):
        """Test that require_provider allows users with broker role."""
        user = User(username="bob", roles=["broker"], token_payload={})
        result = require_provider(user)
        assert result == user
    
    def test_require_provider_without_role(self):
        """Test that require_provider rejects users without provider or broker role."""
        user = User(username="charlie", roles=["consumer"], token_payload={})
        
        with pytest.raises(HTTPException) as exc_info:
            require_provider(user)
        
        assert exc_info.value.status_code == 403
        assert "provider" in exc_info.value.detail.lower() or "broker" in exc_info.value.detail.lower()
    
    def test_require_consumer_with_consumer_role(self):
        """Test that require_consumer allows users with consumer role."""
        user = User(username="dave", roles=["consumer"], token_payload={})
        result = require_consumer(user)
        assert result == user
    
    def test_require_consumer_without_role(self):
        """Test that require_consumer rejects users without consumer role."""
        user = User(username="eve", roles=["provider"], token_payload={})
        
        with pytest.raises(HTTPException) as exc_info:
            require_consumer(user)
        
        assert exc_info.value.status_code == 403
        assert "consumer" in exc_info.value.detail.lower()
    
    def test_require_broker_with_broker_role(self):
        """Test that require_broker allows users with broker role."""
        user = User(username="frank", roles=["broker"], token_payload={})
        result = require_broker(user)
        assert result == user
    
    def test_require_broker_without_role(self):
        """Test that require_broker rejects users without broker role."""
        user = User(username="grace", roles=["consumer"], token_payload={})
        
        with pytest.raises(HTTPException) as exc_info:
            require_broker(user)
        
        assert exc_info.value.status_code == 403
        assert "broker" in exc_info.value.detail.lower()
    
    def test_user_has_role(self):
        """Test User.has_role method."""
        user = User(username="helen", roles=["provider", "consumer"], token_payload={})
        
        assert user.has_role("provider") is True
        assert user.has_role("consumer") is True
        assert user.has_role("broker") is False
    
    def test_user_has_any_role(self):
        """Test User.has_any_role method."""
        user = User(username="ian", roles=["consumer"], token_payload={})
        
        assert user.has_any_role("provider", "consumer") is True
        assert user.has_any_role("provider", "broker") is False
        assert user.has_any_role("consumer") is True
