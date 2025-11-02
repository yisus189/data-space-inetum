import os
import logging
from typing import List, Dict, Optional
import requests
from sqlalchemy.orm import Session

from src.config import settings
from src.models.publication import Publication, PublicationStatus
from src.models.user import User

logger = logging.getLogger(__name__)


def fetch_openmetadata_catalog() -> List[Dict]:
    """
    Fetch datasets from OpenMetadata.
    If OpenMetadata is unreachable, returns mock data.
    """
    if not settings.openmetadata_url:
        logger.warning("OpenMetadata URL not configured, using mock data")
        return get_mock_catalog()
    
    try:
        # Try to fetch from OpenMetadata API
        headers = {}
        if settings.openmetadata_api_key:
            headers["Authorization"] = f"Bearer {settings.openmetadata_api_key}"
        
        # Try tables endpoint
        url = f"{settings.openmetadata_url.rstrip('/')}/api/v1/tables"
        logger.info(f"Fetching catalog from OpenMetadata: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract tables from response
        tables = []
        if isinstance(data, dict):
            if 'data' in data:
                tables = data['data']
            elif 'entities' in data:
                tables = data['entities']
        elif isinstance(data, list):
            tables = data
        
        logger.info(f"Fetched {len(tables)} tables from OpenMetadata")
        return tables
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"OpenMetadata is unreachable: {e}. Using mock data.")
        return get_mock_catalog()
    except Exception as e:
        logger.error(f"Error fetching from OpenMetadata: {e}. Using mock data.")
        return get_mock_catalog()


def get_mock_catalog() -> List[Dict]:
    """Return mock catalog data when OpenMetadata is unavailable"""
    logger.info("Using mock catalog data")
    return [
        {
            "id": "mock-customers-table",
            "name": "customers",
            "fullyQualifiedName": "sample_db.public.customers",
            "displayName": "Customers Table",
            "description": "Customer master data including contact information",
            "tableType": "Regular",
            "columns": [
                {"name": "id", "dataType": "INTEGER", "description": "Customer ID"},
                {"name": "name", "dataType": "VARCHAR", "description": "Customer name"},
                {"name": "email", "dataType": "VARCHAR", "description": "Email address"},
                {"name": "created_at", "dataType": "TIMESTAMP", "description": "Creation timestamp"}
            ],
            "tags": [{"tagFQN": "PII"}, {"tagFQN": "CustomerData"}],
            "owner": {"name": "data-team", "type": "team"}
        },
        {
            "id": "mock-orders-table",
            "name": "orders",
            "fullyQualifiedName": "sample_db.public.orders",
            "displayName": "Orders Table",
            "description": "Customer orders and transactions",
            "tableType": "Regular",
            "columns": [
                {"name": "order_id", "dataType": "INTEGER", "description": "Order ID"},
                {"name": "customer_id", "dataType": "INTEGER", "description": "Customer reference"},
                {"name": "total", "dataType": "DECIMAL", "description": "Order total"},
                {"name": "order_date", "dataType": "DATE", "description": "Order date"}
            ],
            "tags": [{"tagFQN": "SalesData"}, {"tagFQN": "Transactional"}],
            "owner": {"name": "sales-team", "type": "team"}
        },
        {
            "id": "mock-products-table",
            "name": "products",
            "fullyQualifiedName": "sample_db.public.products",
            "displayName": "Products Catalog",
            "description": "Product catalog with pricing and inventory",
            "tableType": "Regular",
            "columns": [
                {"name": "product_id", "dataType": "INTEGER", "description": "Product ID"},
                {"name": "name", "dataType": "VARCHAR", "description": "Product name"},
                {"name": "price", "dataType": "DECIMAL", "description": "Unit price"},
                {"name": "stock", "dataType": "INTEGER", "description": "Stock quantity"}
            ],
            "tags": [{"tagFQN": "ProductData"}, {"tagFQN": "Inventory"}],
            "owner": {"name": "inventory-team", "type": "team"}
        }
    ]


def map_openmetadata_to_publication(item: Dict, publisher_id: str) -> Dict:
    """Map OpenMetadata table to Publication format"""
    # Extract tags
    tags = []
    if 'tags' in item and isinstance(item['tags'], list):
        tags = [tag.get('tagFQN', tag) if isinstance(tag, dict) else tag for tag in item['tags']]
    
    # Extract owner
    owner = item.get('owner', {})
    owner_name = owner.get('name') if isinstance(owner, dict) else str(owner)
    
    # Build schema info from columns
    schema_info = {}
    if 'columns' in item:
        schema_info = {
            'columns': item['columns'],
            'tableType': item.get('tableType', 'Regular')
        }
    
    return {
        'title': item.get('displayName') or item.get('name', 'Untitled'),
        'description': item.get('description', ''),
        'openmetadata_id': item.get('id'),
        'openmetadata_fqn': item.get('fullyQualifiedName'),
        'metadata': {
            'source': 'openmetadata',
            'owner': owner_name,
            'href': item.get('href'),
        },
        'schema_info': schema_info,
        'tags': tags,
        'status': PublicationStatus.PUBLISHED,
        'publisher_id': publisher_id,
    }


def sync_openmetadata_catalog(db: Session, publisher_id: str) -> List[Publication]:
    """
    Sync OpenMetadata catalog to Publications table.
    
    Args:
        db: Database session
        publisher_id: ID of the user who will be listed as publisher
    
    Returns:
        List of created/updated publications
    """
    logger.info("Starting OpenMetadata catalog sync")
    
    # Fetch catalog from OpenMetadata
    items = fetch_openmetadata_catalog()
    
    if not items:
        logger.warning("No items fetched from OpenMetadata")
        return []
    
    publications = []
    
    for item in items:
        try:
            # Map to publication format
            pub_data = map_openmetadata_to_publication(item, publisher_id)
            
            # Check if publication already exists by openmetadata_id
            existing_pub = None
            if pub_data.get('openmetadata_id'):
                existing_pub = db.query(Publication).filter(
                    Publication.openmetadata_id == pub_data['openmetadata_id']
                ).first()
            
            if existing_pub:
                # Update existing publication
                for key, value in pub_data.items():
                    if key != 'id':
                        setattr(existing_pub, key, value)
                db.commit()
                db.refresh(existing_pub)
                publications.append(existing_pub)
                logger.info(f"Updated publication: {existing_pub.title}")
            else:
                # Create new publication
                publication = Publication(**pub_data)
                db.add(publication)
                db.commit()
                db.refresh(publication)
                publications.append(publication)
                logger.info(f"Created publication: {publication.title}")
                
        except Exception as e:
            logger.error(f"Error syncing item {item.get('name', 'unknown')}: {e}")
            continue
    
    logger.info(f"Synced {len(publications)} publications from OpenMetadata")
    return publications
