"""OpenMetadata integration client."""
import os
import logging
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger(__name__)

OPENMETADATA_URL = os.getenv("OPENMETADATA_URL", "http://localhost:8585")
OPENMETADATA_API_KEY = os.getenv("OPENMETADATA_API_KEY", "")


class OpenMetadataClient:
    """Client for OpenMetadata API."""
    
    def __init__(
        self,
        base_url: str = OPENMETADATA_URL,
        api_key: str = OPENMETADATA_API_KEY
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including auth if configured."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=30.0
            )
        return self._client
    
    def list_tables(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List tables/datasets from OpenMetadata."""
        try:
            response = self.client.get(f"/api/v1/tables?limit={limit}")
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, dict):
                if "data" in data:
                    return data["data"]
                elif "entities" in data:
                    return data["entities"]
            elif isinstance(data, list):
                return data
            
            return []
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch tables: {e}")
            return []
    
    def get_table(self, table_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific table by ID or FQN."""
        try:
            # Try by ID first
            response = self.client.get(f"/api/v1/tables/{table_id}")
            if response.status_code == 200:
                return response.json()
            
            # Try by FQN
            response = self.client.get(f"/api/v1/tables/name/{table_id}")
            if response.status_code == 200:
                return response.json()
            
            return None
        except httpx.RequestError as e:
            logger.error(f"Failed to get table {table_id}: {e}")
            return None
    
    def list_databases(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List databases from OpenMetadata."""
        try:
            response = self.client.get(f"/api/v1/databases?limit={limit}")
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data if isinstance(data, list) else []
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch databases: {e}")
            return []
    
    def search(
        self,
        query: str = "*",
        entity_type: str = "table",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search entities in OpenMetadata."""
        try:
            params = {
                "q": query,
                "index": entity_type,
                "size": limit
            }
            response = self.client.get("/api/v1/search/query", params=params)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict) and "hits" in data:
                hits = data["hits"]
                if isinstance(hits, dict) and "hits" in hits:
                    return [h.get("_source", h) for h in hits["hits"]]
            return []
        except httpx.RequestError as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_entity_data_location(self, entity: Dict[str, Any]) -> Optional[str]:
        """Extract data location from entity metadata."""
        # Check for S3/MinIO location in service connection
        if "service" in entity:
            service = entity.get("service", {})
            connection = service.get("connection", {})
            config = connection.get("config", {})
            
            # S3 bucket location
            if "bucketName" in config:
                return f"s3://{config['bucketName']}"
        
        # Check for direct href
        if "href" in entity:
            return entity["href"]
        
        return None
    
    def transform_to_dataset_metadata(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OpenMetadata entity to dataset metadata format."""
        return {
            "source": "openmetadata",
            "source_id": entity.get("id"),
            "source_fqn": entity.get("fullyQualifiedName"),
            "display_name": entity.get("displayName") or entity.get("name"),
            "description": entity.get("description"),
            "owner": entity.get("owner"),
            "tags": [t.get("tagFQN") if isinstance(t, dict) else t for t in (entity.get("tags") or [])],
            "columns": entity.get("columns", []),
            "table_type": entity.get("tableType"),
            "service": entity.get("service", {}).get("name"),
            "database": entity.get("database", {}).get("name"),
            "schema": entity.get("databaseSchema", {}).get("name"),
        }
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


# Global client instance
_client: Optional[OpenMetadataClient] = None


def get_openmetadata_client() -> OpenMetadataClient:
    """Get the global OpenMetadata client instance."""
    global _client
    if _client is None:
        _client = OpenMetadataClient()
    return _client
