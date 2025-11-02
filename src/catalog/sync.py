"""OpenMetadata catalog synchronization."""

import os
import logging
from typing import List, Dict, Any, Optional
import requests
from sqlalchemy.orm import Session

from ..db import PublicationRepository

logger = logging.getLogger(__name__)

OPENMETADATA_URL = os.getenv("OPENMETADATA_URL", "http://localhost:8585")
OPENMETADATA_API_KEY = os.getenv("OPENMETADATA_API_KEY", "")


class OpenMetadataError(Exception):
    """OpenMetadata integration error."""
    pass


def get_mock_catalog_data() -> List[Dict[str, Any]]:
    """Return mock catalog data when OpenMetadata is unavailable."""
    logger.warning("Using mock catalog data - OpenMetadata is unavailable")
    return [
        {
            "id": "mock-customer-table",
            "name": "customers",
            "displayName": "Customer Table",
            "description": "Customer data including contact information and preferences",
            "fullyQualifiedName": "sample_db.public.customers",
            "columns": [
                {"name": "customer_id", "dataType": "INTEGER", "description": "Unique customer ID"},
                {"name": "name", "dataType": "VARCHAR", "description": "Customer full name"},
                {"name": "email", "dataType": "VARCHAR", "description": "Customer email address"},
                {"name": "created_at", "dataType": "TIMESTAMP", "description": "Account creation date"}
            ],
            "tags": ["PII", "customer_data"],
            "owner": "data_team"
        },
        {
            "id": "mock-orders-table",
            "name": "orders",
            "displayName": "Orders Table",
            "description": "Order transactions and details",
            "fullyQualifiedName": "sample_db.public.orders",
            "columns": [
                {"name": "order_id", "dataType": "INTEGER", "description": "Unique order ID"},
                {"name": "customer_id", "dataType": "INTEGER", "description": "Reference to customer"},
                {"name": "order_date", "dataType": "TIMESTAMP", "description": "Date of order"},
                {"name": "total_amount", "dataType": "DECIMAL", "description": "Total order amount"}
            ],
            "tags": ["financial", "orders"],
            "owner": "sales_team"
        },
        {
            "id": "mock-products-table",
            "name": "products",
            "displayName": "Products Catalog",
            "description": "Product inventory and catalog information",
            "fullyQualifiedName": "sample_db.public.products",
            "columns": [
                {"name": "product_id", "dataType": "INTEGER", "description": "Unique product ID"},
                {"name": "product_name", "dataType": "VARCHAR", "description": "Product name"},
                {"name": "category", "dataType": "VARCHAR", "description": "Product category"},
                {"name": "price", "dataType": "DECIMAL", "description": "Product price"}
            ],
            "tags": ["catalog", "inventory"],
            "owner": "product_team"
        }
    ]


def fetch_openmetadata_catalog() -> List[Dict[str, Any]]:
    """Fetch catalog from OpenMetadata API."""
    
    if not OPENMETADATA_URL:
        logger.warning("OPENMETADATA_URL not configured")
        return get_mock_catalog_data()
    
    try:
        # Build headers
        headers = {
            "Content-Type": "application/json",
        }
        if OPENMETADATA_API_KEY:
            headers["Authorization"] = f"Bearer {OPENMETADATA_API_KEY}"
        
        # Call OpenMetadata search/tables endpoint
        url = f"{OPENMETADATA_URL}/api/v1/tables"
        logger.info(f"Fetching catalog from: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            logger.warning(f"OpenMetadata endpoint not found: {url}")
            return get_mock_catalog_data()
        
        response.raise_for_status()
        
        data = response.json()
        tables = data.get("data", [])
        
        if not tables:
            logger.warning("No tables found in OpenMetadata")
            return get_mock_catalog_data()
        
        logger.info(f"Successfully fetched {len(tables)} tables from OpenMetadata")
        return tables
        
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Cannot connect to OpenMetadata: {e}")
        return get_mock_catalog_data()
    except requests.exceptions.Timeout as e:
        logger.warning(f"OpenMetadata request timed out: {e}")
        return get_mock_catalog_data()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching from OpenMetadata: {e}")
        return get_mock_catalog_data()
    except Exception as e:
        logger.error(f"Unexpected error fetching catalog: {e}")
        return get_mock_catalog_data()


def sync_catalog_to_publications(db: Session, user_id: int) -> List[int]:
    """
    Sync OpenMetadata catalog to Publications table.
    
    Returns list of created publication IDs.
    """
    items = fetch_openmetadata_catalog()
    publication_ids = []
    
    for item in items:
        # Map OpenMetadata item to Publication
        title = item.get("displayName") or item.get("name", "Untitled")
        description = item.get("description", "")
        
        # Build metadata
        metadata = {
            "openmetadata_id": item.get("id"),
            "fully_qualified_name": item.get("fullyQualifiedName"),
            "columns": item.get("columns", []),
            "tags": item.get("tags", []),
            "owner": item.get("owner"),
        }
        
        # Create publication
        try:
            pub = PublicationRepository.create(
                db,
                title=title,
                owner_id=user_id,
                description=description,
                metadata=metadata,
                openmetadata_id=item.get("id")
            )
            publication_ids.append(pub.id)
            logger.info(f"Created publication {pub.id} for {title}")
        except Exception as e:
            logger.error(f"Failed to create publication for {title}: {e}")
            continue
    
    logger.info(f"Synced {len(publication_ids)} publications from catalog")
    return publication_ids


def get_catalog_item_by_id(openmetadata_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific catalog item by OpenMetadata ID."""
    
    if not OPENMETADATA_URL:
        # Return from mock data
        mock_items = get_mock_catalog_data()
        for item in mock_items:
            if item.get("id") == openmetadata_id:
                return item
        return None
    
    try:
        headers = {
            "Content-Type": "application/json",
        }
        if OPENMETADATA_API_KEY:
            headers["Authorization"] = f"Bearer {OPENMETADATA_API_KEY}"
        
        url = f"{OPENMETADATA_URL}/api/v1/tables/name/{openmetadata_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Error fetching catalog item {openmetadata_id}: {e}")
        return None
