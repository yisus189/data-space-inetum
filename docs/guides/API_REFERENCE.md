# API Reference

Complete API reference for the Data Space application.

## Base URL

- **Local**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

All endpoints (except `/health`) require authentication using JWT Bearer tokens.

### Get Access Token

**Endpoint**: `POST {KEYCLOAK_URL}/realms/{realm}/protocol/openid-connect/token`

**Request**:
```bash
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" \
  -d "grant_type=password" \
  -d "username=provider-user" \
  -d "password=provider123"
```

**Response**:
```json
{
  "access_token": "eyJhbGc...",
  "expires_in": 300,
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer"
}
```

### Using the Token

Include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/publications
```

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Authentication**: Not required

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "service": "Data Space API"
}
```

---

### Publications

#### POST /publications

Create a new publication.

**Authentication**: Required (provider role)

**Request Body**:
```json
{
  "title": "Customer Dataset",
  "description": "Customer information dataset",
  "metadata": {
    "schema": {
      "fields": [
        {"name": "id", "type": "int"},
        {"name": "name", "type": "string"}
      ]
    }
  }
}
```

**Response**: `201 Created`
```json
{
  "id": "pub-uuid",
  "title": "Customer Dataset",
  "description": "Customer information dataset",
  "metadata": {...},
  "owner_id": "user-uuid",
  "created_at": "2025-10-31T14:00:00Z",
  "updated_at": "2025-10-31T14:00:00Z"
}
```

**Errors**:
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: User doesn't have provider role

#### GET /publications

List all publications.

**Authentication**: Required

**Query Parameters**:
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records (default: 100, max: 100)

**Response**: `200 OK`
```json
[
  {
    "id": "pub-uuid",
    "title": "Customer Dataset",
    "description": "...",
    "metadata": {...},
    "owner_id": "user-uuid",
    "created_at": "2025-10-31T14:00:00Z",
    "updated_at": "2025-10-31T14:00:00Z"
  }
]
```

#### GET /publications/{id}

Get a specific publication.

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "id": "pub-uuid",
  "title": "Customer Dataset",
  ...
}
```

**Errors**:
- `404 Not Found`: Publication doesn't exist

---

### Requests

#### POST /requests

Create a data access request.

**Authentication**: Required (consumer role)

**Request Body**:
```json
{
  "subject": "Request access to customer data",
  "publication_id": "pub-uuid"
}
```

Note: `publication_id` is optional. If not provided, this is a general request.

**Response**: `201 Created`
```json
{
  "id": "req-uuid",
  "subject": "Request access to customer data",
  "publication_id": "pub-uuid",
  "requester_id": "user-uuid",
  "state": "open",
  "created_at": "2025-10-31T14:00:00Z",
  "updated_at": "2025-10-31T14:00:00Z"
}
```

**Errors**:
- `403 Forbidden`: User doesn't have consumer role
- `404 Not Found`: Publication doesn't exist (if publication_id provided)

#### GET /requests

List all requests.

**Authentication**: Required

**Query Parameters**: `skip`, `limit` (same as publications)

**Response**: `200 OK`
```json
[
  {
    "id": "req-uuid",
    "subject": "...",
    "publication_id": "pub-uuid",
    "requester_id": "user-uuid",
    "state": "open",
    "created_at": "2025-10-31T14:00:00Z",
    "updated_at": "2025-10-31T14:00:00Z"
  }
]
```

#### GET /requests/{id}

Get a specific request.

**Authentication**: Required

**Response**: `200 OK`

**Errors**:
- `404 Not Found`: Request doesn't exist

---

### Contracts

#### POST /contracts

Create a contract from a request.

**Authentication**: Required

**Request Body**:
```json
{
  "request_id": "req-uuid",
  "terms": {
    "duration": "1 year",
    "usage": "analytics only",
    "restrictions": "no redistribution"
  }
}
```

**Response**: `201 Created`
```json
{
  "id": "contract-uuid",
  "request_id": "req-uuid",
  "terms": {...},
  "state": "active",
  "signed_at": "2025-10-31T14:00:00Z",
  "signature_method": "implicit_acceptance",
  "created_at": "2025-10-31T14:00:00Z",
  "updated_at": "2025-10-31T14:00:00Z"
}
```

**Side Effects**:
- Request state is updated to "contracted"
- Audit logs are created for contract creation and signing

**Errors**:
- `404 Not Found`: Request doesn't exist

#### GET /contracts

List all contracts.

**Authentication**: Required

**Query Parameters**: `skip`, `limit`

**Response**: `200 OK`

#### GET /contracts/{id}

Get a specific contract.

**Authentication**: Required

**Response**: `200 OK`

**Errors**:
- `404 Not Found`: Contract doesn't exist

---

### Transfers

#### POST /transfers

Create a data transfer with pre-signed S3 URL.

**Authentication**: Required

**Request Body**:
```json
{
  "contract_id": "contract-uuid",
  "destination": "customer-data.csv"
}
```

**Response**: `201 Created`
```json
{
  "id": "transfer-uuid",
  "contract_id": "contract-uuid",
  "destination": "customer-data.csv",
  "state": "in_progress",
  "presigned_url": "https://s3.amazonaws.com/bucket/path?X-Amz-...",
  "s3_key": "transfers/contract-uuid/customer-data.csv",
  "created_at": "2025-10-31T14:00:00Z",
  "completed_at": null
}
```

**Usage**:
1. Get the `presigned_url` from the response
2. Upload your file to that URL using PUT request
3. Mark the transfer as complete (see below)

**Upload Example**:
```bash
curl -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: text/csv" \
  --data-binary "@customer-data.csv"
```

**Errors**:
- `404 Not Found`: Contract doesn't exist
- `400 Bad Request`: Contract is not active

#### GET /transfers

List all transfers.

**Authentication**: Required

**Query Parameters**: `skip`, `limit`

**Response**: `200 OK`

#### GET /transfers/{id}

Get a specific transfer.

**Authentication**: Required

**Response**: `200 OK`

**Errors**:
- `404 Not Found`: Transfer doesn't exist

#### POST /transfers/{id}/complete

Mark a transfer as completed.

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "message": "Transfer completed successfully"
}
```

**Side Effects**:
- Transfer state updated to "completed"
- `completed_at` timestamp set
- Audit log entry created

**Errors**:
- `404 Not Found`: Transfer doesn't exist

---

### Catalog Synchronization

#### POST /sync/catalog

Synchronize catalog from OpenMetadata.

**Authentication**: Required (provider role)

**Response**: `200 OK`
```json
{
  "imported": 3,
  "message": "Successfully imported 3 publications"
}
```

**Behavior**:
- Fetches datasets from OpenMetadata (or uses mocks if not configured)
- Creates Publication records for each dataset
- Links publications to the authenticated user

**Errors**:
- `403 Forbidden`: User doesn't have provider role

---

### Audit Logs

#### GET /audit-logs

List audit logs in reverse chronological order.

**Authentication**: Required

**Query Parameters**: `skip`, `limit`

**Response**: `200 OK`
```json
[
  {
    "id": "log-uuid",
    "event_type": "transfer_completed",
    "payload": {
      "id": "transfer-uuid"
    },
    "user_id": "user-uuid",
    "created_at": "2025-10-31T14:05:00Z"
  },
  {
    "id": "log-uuid-2",
    "event_type": "contract_created",
    "payload": {...},
    "user_id": "user-uuid",
    "created_at": "2025-10-31T14:04:00Z"
  }
]
```

**Event Types**:
- `publication_created`
- `request_created`
- `contract_created`
- `contract_signed_implicit`
- `transfer_initiated`
- `transfer_completed`
- `catalog_synced`

---

## Data Models

### Publication

```typescript
{
  id: string;              // UUID
  title: string;
  description: string | null;
  metadata: object | null;
  owner_id: string;        // User UUID
  created_at: datetime;
  updated_at: datetime;
}
```

### Request

```typescript
{
  id: string;              // UUID
  subject: string;
  publication_id: string | null;
  requester_id: string;    // User UUID
  state: "open" | "contracted" | "rejected";
  created_at: datetime;
  updated_at: datetime;
}
```

### Contract

```typescript
{
  id: string;              // UUID
  request_id: string;
  terms: object | null;
  state: "active" | "terminated" | "expired";
  signed_at: datetime | null;
  signature_method: string | null;
  created_at: datetime;
  updated_at: datetime;
}
```

### Transfer

```typescript
{
  id: string;              // UUID
  contract_id: string;
  destination: string;
  state: "initiated" | "in_progress" | "completed" | "failed";
  presigned_url: string | null;
  s3_key: string | null;
  created_at: datetime;
  completed_at: datetime | null;
}
```

### AuditLog

```typescript
{
  id: string;              // UUID
  event_type: string;
  payload: object;
  user_id: string | null;
  created_at: datetime;
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error description"
}
```

### Common Status Codes

- `200 OK`: Successful GET request
- `201 Created`: Successful POST request
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Currently not implemented. Consider adding for production:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/publications")
@limiter.limit("10/minute")
async def create_publication(...):
    ...
```

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Client Libraries

### Python

```python
import requests

# Authenticate
auth_response = requests.post(
    "http://localhost:8080/realms/dataspace/protocol/openid-connect/token",
    data={
        "client_id": "dataspace-api",
        "client_secret": "dataspace-secret",
        "grant_type": "password",
        "username": "provider-user",
        "password": "provider123",
    }
)
token = auth_response.json()["access_token"]

# Create publication
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/publications",
    headers=headers,
    json={
        "title": "My Dataset",
        "description": "Description",
        "metadata": {}
    }
)
publication = response.json()
```

### JavaScript/TypeScript

```typescript
// Authenticate
const authResponse = await fetch(
  "http://localhost:8080/realms/dataspace/protocol/openid-connect/token",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      client_id: "dataspace-api",
      client_secret: "dataspace-secret",
      grant_type: "password",
      username: "provider-user",
      password: "provider123",
    }),
  }
);
const { access_token } = await authResponse.json();

// Create publication
const response = await fetch("http://localhost:8000/publications", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${access_token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    title: "My Dataset",
    description: "Description",
    metadata: {},
  }),
});
const publication = await response.json();
```

---

## Webhooks (Future Enhancement)

Audit webhook support is configured but not yet implemented:

```python
# src/audit.py
def send_audit_webhook(event: AuditLog):
    if settings.audit_webhook_url:
        requests.post(
            settings.audit_webhook_url,
            json={
                "event_type": event.event_type,
                "payload": event.payload,
                "timestamp": event.created_at.isoformat(),
            }
        )
```

---

## Versioning

Current version: `v1.0.0`

API versioning is not yet implemented. Future versions may use:
- URL versioning: `/api/v1/publications`, `/api/v2/publications`
- Header versioning: `Accept: application/vnd.dataspace.v1+json`

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/yisus189/data-space-inetum/issues
- Documentation: See `/docs` directory
