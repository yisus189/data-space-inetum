import os
import logging
from typing import List, Dict, Optional
import requests
from src.config import settings

logger = logging.getLogger(__name__)

# OpenMetadata integration
# This module provides integration with OpenMetadata for catalog synchronization.
# If OpenMetadata URL is not configured, it uses mock data for development.


def fetch_openmetadata_catalog() -> List[Dict]:
    """
    Fetch datasets from OpenMetadata API.
    
    Returns:
        List of dataset dictionaries from OpenMetadata
    """
    if not settings.openmetadata_url:
        logger.warning("OpenMetadata URL not configured, using mock data")
        return _get_mock_catalog()
    
    try:
        # OpenMetadata API endpoint for tables/datasets
        url = f"{settings.openmetadata_url}/api/v1/tables"
        
        headers = {}
        if settings.openmetadata_api_key:
            headers["Authorization"] = f"Bearer {settings.openmetadata_api_key}"
        
        params = {
            "limit": 100,
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        tables = data.get("data", [])
        
        logger.info(f"Fetched {len(tables)} datasets from OpenMetadata")
        return tables
        
    except requests.RequestException as e:
        logger.error(f"Error fetching from OpenMetadata: {e}")
        logger.info("Falling back to mock data")
        return _get_mock_catalog()


def _get_mock_catalog() -> List[Dict]:
    """
    Return mock catalog data for development/testing.
    
    Returns:
        List of mock dataset dictionaries
    """
    return [
        {
            "name": "customers",
            "displayName": "Customers Table",
            "description": "Customer dataset with personal and contact information",
            "fullyQualifiedName": "default.sample_db.customers",
            "columns": [
                {"name": "id", "dataType": "INT", "description": "Customer ID"},
                {"name": "name", "dataType": "VARCHAR", "description": "Customer name"},
                {"name": "email", "dataType": "VARCHAR", "description": "Customer email"},
            ],
            "tags": [{"tagFQN": "PII.Sensitive"}],
        },
        {
            "name": "orders",
            "displayName": "Orders Table",
            "description": "Orders dataset with transaction information",
            "fullyQualifiedName": "default.sample_db.orders",
            "columns": [
                {"name": "order_id", "dataType": "INT", "description": "Order ID"},
                {"name": "customer_id", "dataType": "INT", "description": "Customer ID"},
                {"name": "amount", "dataType": "DECIMAL", "description": "Order amount"},
                {"name": "order_date", "dataType": "DATE", "description": "Order date"},
            ],
            "tags": [],
        },
        {
            "name": "products",
            "displayName": "Products Table",
            "description": "Product catalog with pricing information",
            "fullyQualifiedName": "default.sample_db.products",
            "columns": [
                {"name": "product_id", "dataType": "INT", "description": "Product ID"},
                {"name": "name", "dataType": "VARCHAR", "description": "Product name"},
                {"name": "price", "dataType": "DECIMAL", "description": "Product price"},
            ],
            "tags": [],
        },
    ]


def map_openmetadata_to_publication(dataset: Dict) -> Dict:
    """
    Map an OpenMetadata dataset to a Publication model.
    
    Args:
        dataset: OpenMetadata dataset dictionary
        
    Returns:
        Publication-compatible dictionary
    """
    return {
        "title": dataset.get("displayName") or dataset.get("name", "Unknown"),
        "description": dataset.get("description", ""),
        "metadata": {
            "source": "openmetadata",
            "fully_qualified_name": dataset.get("fullyQualifiedName", ""),
            "columns": dataset.get("columns", []),
            "tags": dataset.get("tags", []),
            "service": dataset.get("service", {}),
            "database": dataset.get("database", {}),
            "databaseSchema": dataset.get("databaseSchema", {}),
        },
    }


def sync_openmetadata_catalog() -> List[Dict]:
    """
    Sync catalog from OpenMetadata and map to Publications.
    
    Returns:
        List of publication dictionaries ready to be stored
    """
    datasets = fetch_openmetadata_catalog()
    publications = []
    
    for dataset in datasets:
        pub = map_openmetadata_to_publication(dataset)
        publications.append(pub)
    
    logger.info(f"Mapped {len(publications)} publications from OpenMetadata")
    return publications


def fetch_openmetadata_dataset(dataset_fqn: str) -> Optional[Dict]:
    """
    Fetch a specific dataset from OpenMetadata by fully qualified name.
    
    Args:
        dataset_fqn: Fully qualified name of the dataset
        
    Returns:
        Dataset dictionary or None if not found
    """
    if not settings.openmetadata_url:
        logger.warning("OpenMetadata URL not configured")
        return None
    
    try:
        url = f"{settings.openmetadata_url}/api/v1/tables/name/{dataset_fqn}"
        
        headers = {}
        if settings.openmetadata_api_key:
            headers["Authorization"] = f"Bearer {settings.openmetadata_api_key}"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Error fetching dataset {dataset_fqn}: {e}")
        return None

