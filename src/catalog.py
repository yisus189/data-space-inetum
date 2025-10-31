"""
OpenMetadata catalog integration with real REST API support
"""
import os
import logging
from typing import List, Dict, Optional
import requests

logger = logging.getLogger(__name__)

OPENMETADATA_URL = os.getenv("OPENMETADATA_URL", "http://openmetadata:8585")
OPENMETADATA_API_KEY = os.getenv("OPENMETADATA_API_KEY", "")


class OpenMetadataCatalog:
    """OpenMetadata catalog client"""
    
    def __init__(self, base_url: str = OPENMETADATA_URL, api_key: str = OPENMETADATA_API_KEY):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {}
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def is_available(self) -> bool:
        """Check if OpenMetadata is available"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/health",
                headers=self.headers,
                timeout=5
            )
            available = response.status_code == 200
            logger.info(f"OpenMetadata availability check: {'available' if available else 'unavailable'}")
            return available
        except Exception as e:
            logger.warning(f"OpenMetadata not available: {e}")
            return False
    
    def fetch_tables(self, limit: int = 100) -> List[Dict]:
        """Fetch tables/datasets from OpenMetadata"""
        if not self.is_available():
            logger.warning("OpenMetadata not available, returning mock data")
            return self._get_mock_data()
        
        try:
            logger.info(f"Fetching tables from OpenMetadata (limit: {limit})")
            url = f"{self.base_url}/api/v1/tables"
            params = {'limit': limit}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            tables = []
            
            # Parse response - OpenMetadata can return different structures
            if isinstance(data, dict):
                if 'data' in data:
                    tables = data['data']
                elif 'entities' in data:
                    tables = data['entities']
                else:
                    # Try to find a list in the response
                    for value in data.values():
                        if isinstance(value, list):
                            tables = value
                            break
            elif isinstance(data, list):
                tables = data
            
            logger.info(f"Successfully fetched {len(tables)} tables from OpenMetadata")
            return tables
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch tables from OpenMetadata: {e}")
            logger.warning("Falling back to mock data")
            return self._get_mock_data()
    
    def _get_mock_data(self) -> List[Dict]:
        """Return mock catalog data when OpenMetadata is not available"""
        logger.info("Generating mock catalog data")
        return [
            {
                "name": "customers",
                "fullyQualifiedName": "sample_db.customers",
                "displayName": "Customer Dataset",
                "description": "Customer information including demographics and contact details",
                "tableType": "Regular",
                "columns": [
                    {"name": "id", "dataType": "INT", "description": "Customer ID"},
                    {"name": "name", "dataType": "STRING", "description": "Customer name"},
                    {"name": "email", "dataType": "STRING", "description": "Email address"}
                ],
                "tags": [{"tagFQN": "PII"}, {"tagFQN": "Customer"}],
                "owner": {"name": "data-team", "type": "team"}
            },
            {
                "name": "orders",
                "fullyQualifiedName": "sample_db.orders",
                "displayName": "Orders Dataset",
                "description": "Order transactions and history",
                "tableType": "Regular",
                "columns": [
                    {"name": "order_id", "dataType": "INT", "description": "Order ID"},
                    {"name": "customer_id", "dataType": "INT", "description": "Customer ID"},
                    {"name": "amount", "dataType": "DECIMAL", "description": "Order amount"}
                ],
                "tags": [{"tagFQN": "Sales"}],
                "owner": {"name": "data-team", "type": "team"}
            },
            {
                "name": "products",
                "fullyQualifiedName": "sample_db.products",
                "displayName": "Products Catalog",
                "description": "Product catalog with pricing and inventory",
                "tableType": "Regular",
                "columns": [
                    {"name": "product_id", "dataType": "INT", "description": "Product ID"},
                    {"name": "name", "dataType": "STRING", "description": "Product name"},
                    {"name": "price", "dataType": "DECIMAL", "description": "Product price"}
                ],
                "tags": [{"tagFQN": "Inventory"}],
                "owner": {"name": "data-team", "type": "team"}
            }
        ]
    
    def map_to_publication(self, table: Dict) -> Dict:
        """Map OpenMetadata table to Data Space publication format"""
        name = table.get("fullyQualifiedName") or table.get("name") or table.get("id")
        title = table.get("displayName") or name
        description = table.get("description") or ""
        
        # Extract owner information
        owner_info = table.get("owner", {})
        owner_name = None
        if isinstance(owner_info, dict):
            owner_name = owner_info.get("name")
        
        # Extract tags
        tags = table.get("tags", [])
        tag_names = []
        for tag in tags:
            if isinstance(tag, dict):
                tag_names.append(tag.get("tagFQN") or tag.get("name", ""))
            else:
                tag_names.append(str(tag))
        
        # Extract columns/schema
        columns = table.get("columns", [])
        
        publication = {
            "title": title,
            "description": description,
            "metadata": {
                "source": "openmetadata",
                "fullyQualifiedName": name,
                "tableType": table.get("tableType"),
                "tags": tag_names,
                "owner": owner_name,
                "columns": columns,
                "href": table.get("href"),
            }
        }
        
        logger.debug(f"Mapped table '{name}' to publication")
        return publication


def sync_openmetadata_catalog(limit: int = 100) -> List[Dict]:
    """
    Sync catalog from OpenMetadata and return as publications
    This is the main function used by the API endpoint
    """
    logger.info("Starting OpenMetadata catalog sync")
    
    catalog = OpenMetadataCatalog()
    tables = catalog.fetch_tables(limit=limit)
    
    publications = []
    for table in tables:
        try:
            pub = catalog.map_to_publication(table)
            publications.append(pub)
        except Exception as e:
            logger.error(f"Error mapping table to publication: {e}")
            continue
    
    logger.info(f"Catalog sync completed: {len(publications)} publications prepared")
    return publications


def get_catalog_client() -> OpenMetadataCatalog:
    """Get OpenMetadata catalog client instance"""
    return OpenMetadataCatalog()

