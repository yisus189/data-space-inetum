"""
Unit tests for authentication dependencies.
"""
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.auth.dependencies import get_current_user, get_current_user_optional


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""
    
    @pytest.mark.asyncio
    async def test_missing_credentials(self):
        """Test missing credentials raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)
        
        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_valid_token(self):
        """Test valid token returns payload."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid.jwt.token"
        )
        
        mock_payload = {"sub": "user123", "email": "user@example.com"}
        
        with patch('src.auth.dependencies.verify_and_decode') as mock_verify:
            mock_verify.return_value = mock_payload
            
            result = await get_current_user(credentials)
            
            assert result == mock_payload
            mock_verify.assert_called_once_with("valid.jwt.token")
    
    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test invalid token raises HTTPException."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.jwt.token"
        )
        
        with patch('src.auth.dependencies.verify_and_decode') as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)
            
            assert exc_info.value.status_code == 401


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""
    
    @pytest.mark.asyncio
    async def test_missing_credentials_returns_none(self):
        """Test missing credentials returns None."""
        result = await get_current_user_optional(None)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_valid_token_returns_payload(self):
        """Test valid token returns payload."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid.jwt.token"
        )
        
        mock_payload = {"sub": "user123"}
        
        with patch('src.auth.dependencies.verify_and_decode') as mock_verify:
            mock_verify.return_value = mock_payload
            
            result = await get_current_user_optional(credentials)
            
            assert result == mock_payload
    
    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        """Test invalid token returns None instead of raising."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.jwt.token"
        )
        
        with patch('src.auth.dependencies.verify_and_decode') as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            result = await get_current_user_optional(credentials)
            
            assert result is None
