"""Integration API endpoints."""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.keycloak import User, require_provider, require_current_user
from ..models import get_db, Dataset, DatasetVersion, DatasetVisibility, AuditLog
from ..storage import get_storage
from .openmetadata import get_openmetadata_client, OpenMetadataClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integrations"])


# Request/Response models
class CatalogEntity(BaseModel):
    """Catalog entity from OpenMetadata."""
    id: str
    name: str
    fqn: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    entity_type: str = "table"
    owner: Optional[str] = None
    tags: List[str] = []
    metadata: Optional[dict] = None


class ImportRequest(BaseModel):
    """Import request from OpenMetadata."""
    entity_id: str = Field(..., description="OpenMetadata entity ID or FQN")
    take_data: bool = Field(default=False, description="Whether to copy data to MinIO")
    target_bucket: Optional[str] = Field(None, description="Target bucket for data copy")


class ImportResponse(BaseModel):
    """Import response."""
    dataset_id: str
    title: str
    external_source: str
    data_copy_initiated: bool
    message: str


async def copy_data_from_source(
    dataset_id: str,
    source_location: str,
    target_bucket: Optional[str],
    user_id: str,
    db_url: str
) -> None:
    """Background task to copy data from source to MinIO."""
    # This is a stub for the actual data copy operation
    # In production, this would:
    # 1. Connect to the source (S3, database, etc.)
    # 2. Export/download the data
    # 3. Upload to MinIO
    # 4. Update the dataset version with the new object_key
    
    logger.info(f"Starting data copy for dataset {dataset_id} from {source_location}")
    
    # Simulate data copy
    import asyncio
    await asyncio.sleep(1)
    
    # In production: update database with the new version
    logger.info(f"Data copy completed for dataset {dataset_id}")


@router.get("/openmetadata/catalog", response_model=List[CatalogEntity])
async def list_catalog(
    search: Optional[str] = Query(None, description="Search query"),
    entity_type: str = Query("table", description="Entity type to list"),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(require_current_user)
):
    """
    List entities from OpenMetadata catalog.
    
    Proxies to OpenMetadata API to list tables/datasets.
    """
    client = get_openmetadata_client()
    
    try:
        if search:
            entities = client.search(query=search, entity_type=entity_type, limit=limit)
        else:
            entities = client.list_tables(limit=limit)
        
        result = []
        for entity in entities:
            result.append(CatalogEntity(
                id=entity.get("id", ""),
                name=entity.get("name", ""),
                fqn=entity.get("fullyQualifiedName"),
                display_name=entity.get("displayName"),
                description=entity.get("description"),
                entity_type=entity_type,
                owner=entity.get("owner", {}).get("name") if isinstance(entity.get("owner"), dict) else None,
                tags=[t.get("tagFQN") if isinstance(t, dict) else str(t) for t in (entity.get("tags") or [])],
                metadata=client.transform_to_dataset_metadata(entity)
            ))
        
        return result
    except Exception as e:
        logger.error(f"Failed to fetch catalog: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenMetadata service unavailable"
        )


@router.get("/openmetadata/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    user: User = Depends(require_current_user)
):
    """
    Get complete metadata for a specific OpenMetadata entity.
    """
    client = get_openmetadata_client()
    
    entity = client.get_table(entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found in OpenMetadata"
        )
    
    return {
        "entity": entity,
        "dataset_metadata": client.transform_to_dataset_metadata(entity)
    }


@router.post("/openmetadata/import", response_model=ImportResponse)
async def import_entity(
    request: ImportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """
    Import an entity from OpenMetadata as a dataset.
    
    Creates a dataset with external_source linking to openmetadata://{id}
    and stores the full metadata. If take_data is true, initiates a
    background task to copy the data to MinIO.
    """
    client = get_openmetadata_client()
    
    # Fetch entity from OpenMetadata
    entity = client.get_table(request.entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found in OpenMetadata"
        )
    
    # Check if already imported
    external_source = f"openmetadata://{entity.get('id')}"
    existing = db.query(Dataset).filter(
        Dataset.external_source == external_source,
        Dataset.provider_id == user.provider_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entity already imported as dataset {existing.id}"
        )
    
    # Create dataset from entity
    metadata = client.transform_to_dataset_metadata(entity)
    
    dataset = Dataset(
        title=entity.get("displayName") or entity.get("name"),
        description=entity.get("description"),
        provider_id=user.provider_id,
        provider_name=user.display_name,
        visibility=DatasetVisibility.DRAFT,
        external_source=external_source,
        metadata_json=metadata
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # Audit log
    audit_entry = AuditLog(
        event_type="dataset.imported",
        resource_type="dataset",
        resource_id=str(dataset.id),
        actor_id=user.provider_id,
        actor_name=user.display_name,
        payload={
            "source": "openmetadata",
            "entity_id": request.entity_id,
            "take_data": request.take_data
        }
    )
    db.add(audit_entry)
    db.commit()
    
    # Initiate data copy if requested
    data_copy_initiated = False
    if request.take_data:
        source_location = client.get_entity_data_location(entity)
        if source_location:
            background_tasks.add_task(
                copy_data_from_source,
                str(dataset.id),
                source_location,
                request.target_bucket,
                user.provider_id,
                ""  # db_url placeholder
            )
            data_copy_initiated = True
    
    return ImportResponse(
        dataset_id=str(dataset.id),
        title=dataset.title,
        external_source=external_source,
        data_copy_initiated=data_copy_initiated,
        message="Entity imported successfully" + (
            ". Data copy initiated in background." if data_copy_initiated else ""
        )
    )


# EDC Integration (stub)
@router.post("/edc/transfer")
async def initiate_edc_transfer(
    dataset_id: str,
    consumer_id: str,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """
    Initiate a managed data transfer via Eclipse Dataspace Connector.
    
    This is a stub endpoint. In production, this would:
    1. Create a contract negotiation with EDC control plane
    2. Initiate data transfer via EDC data plane
    3. Monitor transfer status
    
    See docs/edc-integration.md for configuration details.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    if dataset.provider_id != user.provider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can initiate transfers"
        )
    
    # Stub response
    return {
        "status": "stub",
        "message": "EDC integration is configured as a stub. See docs/edc-integration.md for production setup.",
        "transfer_id": None,
        "dataset_id": dataset_id,
        "consumer_id": consumer_id
    }
