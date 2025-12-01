# API Documentation

Complete API reference for the Data Space backend.

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints require authentication via Bearer token (JWT from Keycloak).

```bash
# Get token
TOKEN=$(curl -X POST http://localhost:8080/realms/myrealm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=dataspace-ui" \
  -d "username=provider1" \
  -d "password=provider123" | jq -r '.access_token')

# Use token in requests
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/datasets
```

## Datasets API

### Create Dataset

Create a new dataset with file upload.

**Endpoint**: `POST /datasets`  
**Auth**: Provider role required  
**Content-Type**: `multipart/form-data`

**Request**:
```bash
curl -X POST http://localhost:8000/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Customer Data" \
  -F "description=Customer database export" \
  -F "metadata={\"format\":\"csv\",\"rows\":1000}" \
  -F "file=@customers.csv"
```

**Response** (201):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Customer Data",
  "description": "Customer database export",
  "visibility": "draft",
  "object_key": "datasets/uuid/customers.csv"
}
```

### Request Upload URL

Get a presigned URL for direct upload to MinIO.

**Endpoint**: `POST /datasets/upload-request`  
**Auth**: Provider role required

**Request**:
```bash
curl -X POST http://localhost:8000/datasets/upload-request \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Large Dataset" \
  -F "description=Big file upload" \
  -F "filename=data.parquet" \
  -F "content_type=application/parquet"
```

**Response** (200):
```json
{
  "upload_url": "https://minio:9000/dataspace/datasets/uuid/data.parquet?X-Amz-...",
  "object_key": "datasets/uuid/data.parquet",
  "expires_in": 3600
}
```

### List Datasets

List available datasets. Consumers see public datasets only, providers see their own.

**Endpoint**: `GET /datasets`  
**Auth**: Optional

**Query Parameters**:
- `skip`: Offset (default: 0)
- `limit`: Max results (default: 100, max: 100)

**Request**:
```bash
curl http://localhost:8000/datasets?skip=0&limit=10
```

**Response** (200):
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Customer Data",
    "description": "Customer database export",
    "visibility": "public",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### Get Dataset Details

Get complete dataset information including versions.

**Endpoint**: `GET /datasets/{id}`  
**Auth**: Optional (required for non-public datasets)

**Request**:
```bash
curl http://localhost:8000/datasets/550e8400-e29b-41d4-a716-446655440000
```

**Response** (200):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Customer Data",
  "description": "Customer database export",
  "visibility": "public",
  "metadata": {"format": "csv", "rows": 1000},
  "provider_id": "provider-uuid",
  "created_by": "provider1",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "versions": [
    {
      "id": "version-uuid",
      "version": 1,
      "object_key": "datasets/uuid/customers.csv",
      "size": 102400,
      "checksum": "abc123",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### Publish Dataset

Change dataset visibility from draft to public.

**Endpoint**: `POST /datasets/{id}/publish`  
**Auth**: Provider role required (must be owner)

**Request**:
```bash
curl -X POST http://localhost:8000/datasets/550e8400-e29b-41d4-a716-446655440000/publish \
  -H "Authorization: Bearer $TOKEN"
```

**Response** (200):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "visibility": "public",
  "message": "Dataset published successfully"
}
```

### Download Dataset

Get presigned download URL for dataset file.

**Endpoint**: `GET /datasets/{id}/download`  
**Auth**: Required for public datasets, must be owner or have contract for private

**Query Parameters**:
- `version`: Specific version number (default: latest)

**Request**:
```bash
curl http://localhost:8000/datasets/550e8400-e29b-41d4-a716-446655440000/download \
  -H "Authorization: Bearer $TOKEN"
```

**Response** (200):
```json
{
  "download_url": "https://minio:9000/dataspace/datasets/uuid/customers.csv?X-Amz-...",
  "expires_in": 3600,
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": 1
}
```

## OpenMetadata Integration

### Get Catalog

Search and browse OpenMetadata catalog.

**Endpoint**: `GET /integrations/openmetadata/catalog`  
**Auth**: Not required

**Query Parameters**:
- `query`: Search query (default: "*")
- `page`: Page number (default: 1)
- `limit`: Results per page (default: 20, max: 100)

**Request**:
```bash
curl "http://localhost:8000/integrations/openmetadata/catalog?query=customers&page=1&limit=20"
```

**Response** (200):
```json
{
  "items": [
    {
      "id": "entity-uuid",
      "name": "customers",
      "display_name": "Customers Table",
      "description": "Customer data from CRM",
      "type": "table",
      "service": "postgres",
      "database": "production",
      "tags": ["pii", "customer"]
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

### Get Entity Details

Get detailed metadata for an OpenMetadata entity.

**Endpoint**: `GET /integrations/openmetadata/entities/{id}`  
**Auth**: Not required

**Request**:
```bash
curl http://localhost:8000/integrations/openmetadata/entities/entity-uuid
```

**Response** (200):
```json
{
  "id": "entity-uuid",
  "name": "customers",
  "display_name": "Customers Table",
  "description": "Customer data from CRM",
  "type": "Regular",
  "columns": [
    {
      "name": "id",
      "type": "INTEGER",
      "description": "Customer ID"
    },
    {
      "name": "email",
      "type": "VARCHAR",
      "description": "Customer email"
    }
  ],
  "service": "postgres",
  "database": "production",
  "schema": "public",
  "tags": ["pii"],
  "owner": {"name": "data-team"}
}
```

### Import Entity

Import an OpenMetadata entity as a dataset.

**Endpoint**: `POST /integrations/openmetadata/import`  
**Auth**: Provider role required

**Request**:
```bash
curl -X POST http://localhost:8000/integrations/openmetadata/import \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "entity-uuid",
    "take_data": false
  }'
```

**Response** (200):
```json
{
  "id": "dataset-uuid",
  "title": "Customers Table",
  "entity_id": "entity-uuid",
  "linked": true,
  "message": "Dataset created with OpenMetadata link"
}
```

## Policies API

### Create Policy

Create an ODRL policy for a dataset.

**Endpoint**: `POST /policies`  
**Auth**: Provider role required

**Request**:
```bash
curl -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "dataset-uuid",
    "odrl_json": {
      "@context": "http://www.w3.org/ns/odrl.jsonld",
      "@type": "Offer",
      "permission": [{
        "action": "use",
        "constraint": [{
          "leftOperand": "purpose",
          "operator": "eq",
          "rightOperand": "research"
        }]
      }]
    }
  }'
```

**Response** (200):
```json
{
  "id": "policy-uuid",
  "dataset_id": "dataset-uuid",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### List Policies

List policies, optionally filtered by dataset.

**Endpoint**: `GET /policies`  
**Auth**: Not required

**Query Parameters**:
- `dataset_id`: Filter by dataset
- `skip`: Offset
- `limit`: Max results

**Request**:
```bash
curl "http://localhost:8000/policies?dataset_id=dataset-uuid"
```

## Contracts API

### Create Contract

Create a contract (consumer initiates).

**Endpoint**: `POST /contracts`  
**Auth**: Consumer role required

**Request**:
```bash
curl -X POST http://localhost:8000/contracts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "dataset-uuid",
    "policy_id": "policy-uuid",
    "odrl_json": { /* contract terms */ }
  }'
```

### Accept Contract

Accept a contract (provider accepts).

**Endpoint**: `POST /contracts/{id}/accept`  
**Auth**: Provider role required

**Request**:
```bash
curl -X POST http://localhost:8000/contracts/contract-uuid/accept \
  -H "Authorization: Bearer $TOKEN"
```

### List Contracts

List contracts for current user.

**Endpoint**: `GET /contracts`  
**Auth**: Consumer role required

## Monitoring API

### Prometheus Metrics

**Endpoint**: `GET /metrics`  
**Auth**: Not required

Returns Prometheus-formatted metrics.

### Health Check

**Endpoint**: `GET /metrics/health`  
**Auth**: Not required

```json
{
  "status": "healthy",
  "timestamp": 1704110400.0
}
```

### Readiness Check

**Endpoint**: `GET /metrics/readiness`  
**Auth**: Not required

```json
{
  "status": "ready",
  "timestamp": 1704110400.0
}
```

## Error Responses

All endpoints may return these error responses:

**401 Unauthorized**:
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden**:
```json
{
  "detail": "Provider role required"
}
```

**404 Not Found**:
```json
{
  "detail": "Dataset not found"
}
```

**500 Internal Server Error**:
```json
{
  "error": "Internal server error",
  "detail": "Error message"
}
```

## Rate Limiting

Currently no rate limiting is implemented. For production, consider adding rate limiting middleware.

## Pagination

List endpoints support pagination:
- `skip`: Number of items to skip (offset)
- `limit`: Maximum items to return (max 100)

Example:
```bash
# Get items 20-40
curl "http://localhost:8000/datasets?skip=20&limit=20"
```

## Interactive Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation.
