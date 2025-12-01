# Data Space - IDSA & DSSC Compliant

A complete Data Space solution following IDSA and DSSC principles, enabling secure data sharing between providers and consumers with full policy enforcement.

## Features

- **Authentication & RBAC**: Keycloak OIDC integration with provider/consumer roles
- **Dataset Management**: Upload, version, and publish datasets with visibility controls
- **OpenMetadata Integration**: Import entities from catalog with optional data copy
- **MinIO Storage**: Object storage with presigned URL support for direct uploads
- **ODRL Policies**: Policy-based access control with usage policies (JSON-LD)
- **Contract Management**: Implicit signatures, acceptance tracking, and audit logging
- **EDC Ready**: Stub integration for Eclipse Dataspace Connector
- **React Frontend**: Modern UI with Material-UI for providers and consumers

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### 1. Clone and Configure

```bash
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Copy environment configuration
cp .env.example .env
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- MinIO object storage (ports 9000, 9001)
- Keycloak identity provider (port 8180)
- Backend API (port 8000)
- Frontend UI (port 3000)

### 3. Wait for Services

```bash
# Check service health
docker-compose ps
docker-compose logs -f api
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Keycloak Admin**: http://localhost:8180/admin (admin/admin)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### 5. Test Users

The Keycloak realm comes with pre-configured users:

| Username | Password | Roles |
|----------|----------|-------|
| provider-user | password | provider, consumer |
| consumer-user | password | consumer |
| admin-user | password | admin, provider, consumer |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│                   - Provider Dashboard                          │
│                   - Consumer Catalog                            │
│                   - Dataset Management                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API (FastAPI)                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  Auth     │ │ Datasets  │ │ Contracts │ │Integration│       │
│  │  Module   │ │  API      │ │   API     │ │   API     │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
│        │             │             │             │              │
│        └─────────────┴─────────────┴─────────────┘              │
│                              │                                  │
│                    ┌─────────┴─────────┐                        │
│                    │   ODRL Evaluator  │                        │
│                    └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Keycloak   │       │  PostgreSQL │       │    MinIO    │
│   (OIDC)    │       │  (Database) │       │  (Storage)  │
└─────────────┘       └─────────────┘       └─────────────┘
                                                   │
                              ┌────────────────────┘
                              ▼
                      ┌─────────────┐
                      │OpenMetadata │
                      │  (Optional) │
                      └─────────────┘
```

## API Endpoints

### Datasets

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /datasets | Create dataset (provider) |
| GET | /datasets | List datasets (public + own) |
| GET | /datasets/{id} | Get dataset details |
| PATCH | /datasets/{id} | Update dataset |
| POST | /datasets/{id}/publish | Publish dataset |
| GET | /datasets/{id}/download | Get download URL |

### Storage

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /storage/presign | Get presigned upload URL |

### OpenMetadata Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /integrations/openmetadata/catalog | List catalog entities |
| GET | /integrations/openmetadata/entities/{id} | Get entity details |
| POST | /integrations/openmetadata/import | Import entity as dataset |

### Contracts & Policies

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /contracts/policies | Create ODRL policy |
| GET | /contracts/policies | List policies |
| POST | /contracts | Create contract request |
| GET | /contracts | List contracts |
| POST | /contracts/{id}/accept | Accept contract |
| POST | /contracts/check-access/{dataset_id} | Check access rights |

## Development

### Backend Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run API locally
uvicorn src.main:app --reload --port 8000

# Run tests
pytest tests/unit/ -v
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dataspace

# Keycloak
KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=myrealm
KEYCLOAK_CLIENT_ID=dataspace-ui

# MinIO
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=dataspace

# OpenMetadata (optional)
OPENMETADATA_URL=http://localhost:8585
OPENMETADATA_API_KEY=

# EDC (optional)
EDC_CONTROL_PLANE_URL=http://localhost:19193/management
```

## Testing

### Unit Tests

```bash
pytest tests/unit/ -v
```

### E2E Smoke Tests

```bash
./scripts/smoke_test.sh
```

## ODRL Policy Examples

### Basic Usage Policy

```json
{
  "@context": "http://www.w3.org/ns/odrl.jsonld",
  "@type": "Policy",
  "uid": "urn:policy:research-only",
  "permission": [{
    "action": "use",
    "target": "urn:data:dataset-123",
    "constraint": [{
      "leftOperand": "purpose",
      "operator": "eq",
      "rightOperand": "research"
    }]
  }]
}
```

### Time-Limited Access

```json
{
  "@context": "http://www.w3.org/ns/odrl.jsonld",
  "@type": "Policy",
  "permission": [{
    "action": ["use", "read"],
    "target": "urn:data:dataset-123",
    "constraint": [{
      "leftOperand": "dateTime",
      "operator": "lteq",
      "rightOperand": "2024-12-31T23:59:59Z"
    }]
  }]
}
```

## License

Apache-2.0

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.