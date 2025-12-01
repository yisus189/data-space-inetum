# Data Space Inetum - IDSA & DSSC Compliant

A complete, production-ready Data Space implementation following IDSA (International Data Spaces Association) and DSSC (Data Spaces Support Centre) principles.

## Features

### 🔐 Authentication & Authorization
- **Keycloak OIDC Integration**: Robust JWT validation with JWKS caching (TTL, ETag)
- **Role-Based Access Control**: Provider and Consumer roles
- **Token Claims Mapping**: `sub` → `provider_id`, `preferred_username` → display name

### 💾 Storage
- **MinIO/S3 Integration**: Enterprise object storage
- **Presigned URLs**: Direct client-to-storage upload/download
- **Server-side Fallback**: Direct streaming for compatibility

### 📊 Datasets API
- **POST /datasets**: Create dataset metadata and versions (provider only)
- **GET /datasets**: List public datasets (consumers) or own datasets (providers)
- **GET /datasets/{id}**: Get dataset details with versions and provenance
- **POST /datasets/{id}/publish**: Publish dataset with audit logging
- **GET /datasets/{id}/download**: Get presigned download URL with authorization

### 🔄 OpenMetadata Integration
- **GET /integrations/openmetadata/catalog**: Proxy catalog with search/pagination
- **GET /integrations/openmetadata/entities/{id}**: Get entity metadata
- **POST /integrations/openmetadata/import**: Import datasets from OpenMetadata

### 📜 Policies & Contracts (EDC Compatible)
- **ODRL Policy Engine**: Simple policy evaluator for access control
- **Contract Negotiation**: Create and accept contracts
- **EDC Stub**: Eclipse Dataspace Connector integration endpoints

### 📈 Observability
- **Prometheus Metrics**: Request counts, durations, upload/download tracking
- **Structured Logging**: JSON logs with request IDs
- **Audit Logs**: All actions logged to database

## Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB+ RAM (for all services)

### 1. Clone and Configure

```bash
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Copy environment template
cp .env.example .env

# Edit .env with your configuration (optional for development)
```

### 2. Start All Services

```bash
docker-compose up -d

# Wait for services to be ready (1-2 minutes)
docker-compose logs -f
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Keycloak**: http://localhost:8080 (admin/admin)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **OpenMetadata**: http://localhost:8585
- **Prometheus Metrics**: http://localhost:8000/metrics

### 3. Initialize Database

```bash
# Run database migrations
docker-compose exec api python scripts/init_db.py
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/metrics/health

# List public datasets
curl http://localhost:8000/datasets

# Run E2E smoke tests
python tests/smoke_test.py
```

## Authentication

### Get Access Token from Keycloak

```bash
# Provider login
curl -X POST http://localhost:8080/realms/myrealm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=dataspace-ui" \
  -d "username=provider1" \
  -d "password=provider123"

# Extract access_token from response
export TOKEN="<your_access_token>"
```

### Use Token in Requests

```bash
# Create dataset (provider only)
curl -X POST http://localhost:8000/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=My Dataset" \
  -F "description=Test dataset" \
  -F "file=@data.csv"

# Publish dataset
curl -X POST http://localhost:8000/datasets/{dataset_id}/publish \
  -H "Authorization: Bearer $TOKEN"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Space Inetum                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Frontend  │  │  FastAPI API │  │   PostgreSQL    │   │
│  │ (React+MUI) │─▶│   Backend    │─▶│    Database     │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│                           │                                  │
│                           ├─────▶ MinIO (Object Storage)    │
│                           │                                  │
│                           ├─────▶ Keycloak (OIDC Auth)      │
│                           │                                  │
│                           ├─────▶ OpenMetadata (Catalog)    │
│                           │                                  │
│                           └─────▶ Redis (Cache)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Datasets
- `POST /datasets` - Create dataset (provider)
- `POST /datasets/upload-request` - Request presigned upload URL
- `GET /datasets` - List datasets
- `GET /datasets/{id}` - Get dataset details
- `POST /datasets/{id}/publish` - Publish dataset
- `GET /datasets/{id}/download` - Get download URL

### OpenMetadata Integration
- `GET /integrations/openmetadata/catalog` - Search catalog
- `GET /integrations/openmetadata/entities/{id}` - Get entity
- `POST /integrations/openmetadata/import` - Import dataset

### Policies & Contracts
- `POST /policies` - Create policy (provider)
- `GET /policies` - List policies
- `POST /contracts` - Create contract (consumer)
- `POST /contracts/{id}/accept` - Accept contract (provider)
- `GET /contracts` - List contracts

### EDC Integration (Stub)
- `POST /edc/catalog` - Request EDC catalog
- `POST /edc/negotiate` - Initiate contract negotiation
- `GET /edc/negotiations/{id}` - Get negotiation status
- `POST /edc/transfer` - Initiate data transfer

### Monitoring
- `GET /metrics` - Prometheus metrics
- `GET /metrics/health` - Health check
- `GET /metrics/readiness` - Readiness check

## Development

### Run Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Linting

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/ --max-line-length=120

# Type checking
mypy src/
```

### Local Development Without Docker

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://dataspace_user:changeme@localhost:5432/dataspace"
export KEYCLOAK_URL="http://localhost:8080"
# ... other vars from .env.example

# Run API
uvicorn src.main:app --reload
```

## Configuration

All configuration is via environment variables. See `.env.example` for full list.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `KEYCLOAK_URL` | Keycloak server URL | http://keycloak:8080 |
| `KEYCLOAK_REALM` | Keycloak realm name | myrealm |
| `KEYCLOAK_CLIENT_ID` | OAuth client ID | dataspace-ui |
| `MINIO_ENDPOINT` | MinIO endpoint | minio:9000 |
| `MINIO_BUCKET` | S3 bucket name | dataspace |
| `OPENMETADATA_URL` | OpenMetadata server URL | http://openmetadata:8585 |
| `JWKS_CACHE_TTL` | JWKS cache TTL (seconds) | 3600 |
| `PRESIGNED_URL_EXPIRY` | Presigned URL expiry (seconds) | 3600 |

## Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong secrets for `KEYCLOAK_CLIENT_SECRET`
- [ ] Enable HTTPS (TLS termination at load balancer or reverse proxy)
- [ ] Set `MINIO_SECURE=true` and configure MinIO TLS
- [ ] Configure PostgreSQL with SSL
- [ ] Set up database backups
- [ ] Enable Keycloak realm audit logging
- [ ] Review and harden ODRL policies
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting

### Kubernetes Deployment

See `docs/kubernetes/` for Helm charts and deployment guides (TODO).

## EDC Integration

This Data Space provides stub endpoints compatible with Eclipse Dataspace Connector (EDC). To integrate with a real EDC instance:

1. Deploy EDC connector
2. Configure EDC Management API URL in `.env`
3. Map our datasets to EDC assets
4. Configure EDC policies
5. See `src/app/routers/edc.py` for detailed integration guide

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure CI passes
5. Submit a pull request

## License

Apache License 2.0 - See LICENSE file

## Support

- Issues: https://github.com/yisus189/data-space-inetum/issues
- Documentation: See `docs/` directory
- IDSA Specification: https://github.com/International-Data-Spaces-Association/IDS-G

## Acknowledgments

Built following IDSA and DSSC principles. Integrates with:
- Eclipse Dataspace Connector (EDC)
- OpenMetadata
- Keycloak
- MinIO