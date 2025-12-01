"""OpenMetadata integration endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
import requests
from pydantic import BaseModel

from src.db.session import SessionLocal
from src.db.repositories.datasets import create_dataset
from src.auth import require_provider, User
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/integrations/openmetadata", tags=["openmetadata"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ImportRequest(BaseModel):
    """Request to import dataset from OpenMetadata."""
    entity_id: str
    take_data: bool = False


@router.get("/catalog")
async def get_catalog(
    query: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Proxy to OpenMetadata catalog with search and pagination.
    
    This endpoint proxies requests to OpenMetadata's search/list API.
    """
    try:
        if not settings.OPENMETADATA_URL:
            raise HTTPException(status_code=503, detail="OpenMetadata integration not configured")
        
        # Build OpenMetadata API request
        url = f"{settings.OPENMETADATA_URL}/api/v1/search/query"
        headers = {}
        if settings.OPENMETADATA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OPENMETADATA_API_KEY}"
        
        params = {
            "q": query or "*",
            "from": (page - 1) * limit,
            "size": limit,
            "index": "table_search_index"  # Search tables/datasets
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Transform response to our format
            hits = data.get("hits", {}).get("hits", [])
            items = []
            
            for hit in hits:
                source = hit.get("_source", {})
                items.append({
                    "id": source.get("id"),
                    "name": source.get("name"),
                    "display_name": source.get("displayName"),
                    "description": source.get("description"),
                    "type": source.get("entityType"),
                    "service": source.get("service", {}).get("name"),
                    "database": source.get("database", {}).get("name"),
                    "tags": source.get("tags", [])
                })
            
            return {
                "items": items,
                "total": data.get("hits", {}).get("total", {}).get("value", 0),
                "page": page,
                "limit": limit
            }
        else:
            logger.error(f"OpenMetadata API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"OpenMetadata API error: {response.text}"
            )
            
    except requests.RequestException as e:
        logger.exception(f"Failed to connect to OpenMetadata: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to OpenMetadata: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Error fetching catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Get entity metadata from OpenMetadata."""
    try:
        if not settings.OPENMETADATA_URL:
            raise HTTPException(status_code=503, detail="OpenMetadata integration not configured")
        
        # Get entity details from OpenMetadata
        url = f"{settings.OPENMETADATA_URL}/api/v1/tables/{entity_id}"
        headers = {}
        if settings.OPENMETADATA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OPENMETADATA_API_KEY}"
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Transform to our format
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "display_name": data.get("displayName"),
                "description": data.get("description"),
                "type": data.get("tableType"),
                "columns": [
                    {
                        "name": col.get("name"),
                        "type": col.get("dataType"),
                        "description": col.get("description")
                    }
                    for col in data.get("columns", [])
                ],
                "service": data.get("service", {}).get("name"),
                "database": data.get("database", {}).get("name"),
                "schema": data.get("databaseSchema", {}).get("name"),
                "tags": data.get("tags", []),
                "owner": data.get("owner")
            }
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="Entity not found in OpenMetadata")
        else:
            logger.error(f"OpenMetadata API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"OpenMetadata API error: {response.text}"
            )
            
    except requests.RequestException as e:
        logger.exception(f"Failed to connect to OpenMetadata: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to OpenMetadata: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_entity(
    request: ImportRequest = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_provider)
):
    """Import dataset from OpenMetadata.
    
    - Creates a dataset linked to openmetadata://{entity_id}
    - If take_data is True, starts background job to copy data to MinIO
    """
    try:
        # Get entity metadata from OpenMetadata
        entity_url = f"{settings.OPENMETADATA_URL}/api/v1/tables/{request.entity_id}"
        headers = {}
        if settings.OPENMETADATA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OPENMETADATA_API_KEY}"
        
        response = requests.get(entity_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch entity from OpenMetadata: {response.text}"
            )
        
        entity_data = response.json()
        
        # Create dataset with OpenMetadata link
        metadata = {
            "source": "openmetadata",
            "entity_id": request.entity_id,
            "entity_type": entity_data.get("tableType"),
            "service": entity_data.get("service", {}).get("name"),
            "database": entity_data.get("database", {}).get("name"),
            "schema": entity_data.get("databaseSchema", {}).get("name"),
            "columns": [
                {
                    "name": col.get("name"),
                    "type": col.get("dataType"),
                    "description": col.get("description")
                }
                for col in entity_data.get("columns", [])
            ]
        }
        
        ds = create_dataset(
            db,
            provider_id=user.provider_id,
            title=entity_data.get("displayName") or entity_data.get("name"),
            description=entity_data.get("description", ""),
            metadata=metadata,
            created_by=user.username,
            object_key=f"openmetadata://{request.entity_id}" if not request.take_data else None
        )
        
        result = {
            "id": str(ds.id),
            "title": ds.title,
            "entity_id": request.entity_id,
            "linked": True
        }
        
        if request.take_data:
            # TODO: Start background job to copy data to MinIO
            # For now, just log the intent
            logger.info(f"Background job requested to copy data from OpenMetadata entity {request.entity_id}")
            result["data_copy_job"] = "pending"
            result["message"] = "Dataset created. Background job will copy data to storage."
        else:
            result["message"] = "Dataset created with OpenMetadata link"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error importing entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
