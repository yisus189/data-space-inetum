"""OpenMetadata catalog integration."""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime

OPENMETADATA_URL = os.getenv("OPENMETADATA_URL", "http://localhost:8585")
OPENMETADATA_API_KEY = os.getenv("OPENMETADATA_API_KEY", "")


class OpenMetadataClient:
    """Client for OpenMetadata REST API."""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or OPENMETADATA_URL).rstrip('/')
        self.api_key = api_key or OPENMETADATA_API_KEY
        self.session = requests.Session()
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def fetch_tables(self, limit: int = 100) -> List[Dict]:
        """Fetch tables from OpenMetadata."""
        if not self.base_url:
            return []
        
        try:
            url = f"{self.base_url}/api/v1/tables"
            params = {'limit': limit}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, dict):
                # Try different possible keys
                if 'data' in data:
                    return data['data'] if isinstance(data['data'], list) else []
                elif 'entities' in data:
                    return data['entities']
                else:
                    # Look for any list value
                    for value in data.values():
                        if isinstance(value, list):
                            return value
            elif isinstance(data, list):
                return data
            
            return []
        except Exception as e:
            print(f"Error fetching tables from OpenMetadata: {e}")
            return []
    
    def get_table_details(self, fqn: str) -> Optional[Dict]:
        """Get detailed information about a specific table."""
        if not self.base_url:
            return None
        
        try:
            url = f"{self.base_url}/api/v1/tables/name/{fqn}"
            params = {'fields': 'columns,tableConstraints,tags,owner,usageSummary'}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching table details for {fqn}: {e}")
            return None


def map_table_to_publication(table: Dict) -> Dict:
    """Map OpenMetadata table to Publication format."""
    fqn = table.get('fullyQualifiedName') or table.get('name') or table.get('id', '')
    title = table.get('displayName') or table.get('name') or fqn
    description = table.get('description', '')
    
    # Extract schema information
    columns = table.get('columns', [])
    schema = {
        'columns': [
            {
                'name': col.get('name'),
                'type': col.get('dataType'),
                'description': col.get('description', ''),
                'nullable': col.get('nullable', True)
            }
            for col in columns
        ]
    }
    
    # Extract tags/keywords
    tags = table.get('tags', [])
    keywords = [tag.get('tagFQN') if isinstance(tag, dict) else tag for tag in tags]
    
    # Extract owner information
    owner = table.get('owner', {})
    owner_name = None
    if isinstance(owner, dict):
        owner_name = owner.get('name') or owner.get('displayName')
    
    # Extract lineage if available
    lineage = None
    if 'upstream' in table or 'downstream' in table:
        lineage = {
            'upstream': table.get('upstream', []),
            'downstream': table.get('downstream', [])
        }
    
    # Build metadata
    metadata = {
        'source': 'openmetadata',
        'tableType': table.get('tableType', 'Table'),
        'database': table.get('database', {}).get('name') if isinstance(table.get('database'), dict) else None,
        'service': table.get('service', {}).get('name') if isinstance(table.get('service'), dict) else None,
        'keywords': keywords,
        'owner': owner_name,
        'href': table.get('href'),
        'synced_at': datetime.utcnow().isoformat()
    }
    
    return {
        'title': title,
        'description': description,
        'openmetadata_fqn': fqn,
        'schema': schema,
        'lineage': lineage,
        'metadata': metadata
    }


def fetch_and_map_catalog(client: OpenMetadataClient = None, limit: int = 100) -> List[Dict]:
    """Fetch catalog from OpenMetadata and map to Publication format."""
    if client is None:
        client = OpenMetadataClient()
    
    tables = client.fetch_tables(limit=limit)
    publications = [map_table_to_publication(table) for table in tables]
    
    return publications
