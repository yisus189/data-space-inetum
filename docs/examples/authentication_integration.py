"""
Example of integrating authentication into existing endpoints.

This file demonstrates how to protect endpoints with JWT authentication
using the new authentication dependencies.
"""
from fastapi import FastAPI, Depends, HTTPException
from typing import Optional
from src.auth.dependencies import get_current_user, get_current_user_optional

# Example 1: Protected endpoint (requires authentication)
def example_protected_endpoint():
    """
    Example of a protected endpoint that requires authentication.
    
    Usage in main.py:
        @app.post("/publications", status_code=201)
        def create_publication(
            p: PublicationIn, 
            user: dict = Depends(get_current_user)
        ):
            pid = str(uuid.uuid4())
            PUBLICATIONS[pid] = {
                "id": pid, 
                "title": p.title, 
                "description": p.description, 
                "metadata": p.metadata,
                "created_by": user["sub"]  # Add user info
            }
            audit("publication_created", PUBLICATIONS[pid])
            return PUBLICATIONS[pid]
    """
    pass


# Example 2: Optional authentication (works with or without token)
def example_optional_auth_endpoint():
    """
    Example of an endpoint with optional authentication.
    
    Usage in main.py:
        @app.get("/publications")
        def list_publications(user: Optional[dict] = Depends(get_current_user_optional)):
            publications = list(PUBLICATIONS.values())
            # If authenticated, could filter by user
            if user:
                # User is authenticated, could show more details or filter
                return {
                    "publications": publications,
                    "user": user["sub"]
                }
            # Anonymous access - return basic list
            return {"publications": publications}
    """
    pass


# Example 3: Custom authorization logic
def example_authorization():
    """
    Example of custom authorization based on token claims.
    
    Usage in main.py:
        async def require_admin(user: dict = Depends(get_current_user)) -> dict:
            roles = user.get("realm_access", {}).get("roles", [])
            if "admin" not in roles:
                raise HTTPException(
                    status_code=403, 
                    detail="Admin access required"
                )
            return user
        
        @app.delete("/publications/{pub_id}")
        def delete_publication(
            pub_id: str, 
            user: dict = Depends(require_admin)
        ):
            if pub_id not in PUBLICATIONS:
                raise HTTPException(status_code=404, detail="Publication not found")
            del PUBLICATIONS[pub_id]
            audit("publication_deleted", {"id": pub_id, "by": user["sub"]})
            return {"status": "deleted"}
    """
    pass


# Example 4: Testing authenticated endpoints
def example_testing():
    """
    Example of testing authenticated endpoints.
    
    Test example:
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        
        def test_protected_endpoint():
            client = TestClient(app)
            
            # Mock the verify_and_decode function
            with patch('src.auth.dependencies.verify_and_decode') as mock_verify:
                mock_verify.return_value = {"sub": "user123"}
                
                response = client.post(
                    "/publications",
                    json={"title": "Test", "description": "Test"},
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 201
                assert response.json()["created_by"] == "user123"
    """
    pass


# Example 5: OpenAPI/Swagger documentation
def example_openapi_config():
    """
    Example of configuring OpenAPI for authentication.
    
    In main.py, update the FastAPI app initialization:
        app = FastAPI(
            title="Data Space API (IDS/DSSC)",
            swagger_ui_init_oauth={
                "clientId": "data-space-api",
                "appName": "Data Space API",
            },
            swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
        )
        
    This enables the "Authorize" button in Swagger UI to test
    authenticated endpoints with real tokens.
    """
    pass
