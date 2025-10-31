# Data Space - IDSA & DSSC Compliant Implementation

**Console-First Data Space with Full Audit Trail**

A complete, production-ready Data Space implementation following IDSA (International Data Spaces Association) and DSSC (Data Spaces Support Centre) principles. Optimized for console usage with comprehensive logging and clear operational visibility.

## Features

- **🔐 Authentication**: Keycloak OIDC integration with role-based access (provider, consumer, broker)
- **📊 Data Catalog**: Real OpenMetadata integration for dataset discovery
- **📝 Publications**: Publish and manage data offerings
- **🤝 Contracts**: Implicit digital contract signing with audit trail
- **📦 Transfers**: Secure S3/MinIO presigned URLs for data transfer
- **🔍 Audit Log**: Persistent, append-only audit trail for all operations
- **🖥️ CLI Tool**: Rich console interface for all operations
- **🚀 Docker Compose**: One-command deployment with all services

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Space API                            │
│  (FastAPI + SQLAlchemy + Alembic + Comprehensive Logging)        │
└──────────┬──────────────┬──────────────┬────────────────────────┘
           │              │              │
    ┌──────▼─────┐ ┌─────▼──────┐ ┌────▼────────┐
    │ PostgreSQL │ │  Keycloak  │ │    MinIO    │
    │  Database  │ │    OIDC    │ │   S3 Store  │
    └────────────┘ └────────────┘ └─────────────┘
           │
    ┌──────▼──────────┐
    │  OpenMetadata   │
    │  Data Catalog   │
    └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### 1. Start All Services

```bash
# Clone the repository
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Start all services with Docker Compose
docker-compose up -d

# Wait for services to be ready (this may take a few minutes)
docker-compose logs -f api
```

### 2. Access Services

- **Data Space API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Keycloak Admin**: http://localhost:8080 (admin/admin)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **OpenMetadata**: http://localhost:8585

### 3. Get Authentication Token

The system uses Keycloak for authentication. Get a token using one of the pre-configured users:

```bash
# Provider user (can publish datasets)
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" \
  -d "grant_type=password" \
  -d "username=provider-user" \
  -d "password=provider123" | jq -r '.access_token'

# Consumer user (can request data)
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" \
  -d "grant_type=password" \
  -d "username=consumer-user" \
  -d "password=consumer123" | jq -r '.access_token'
```

Save the token for use with the API or CLI:

```bash
export DATASPACE_TOKEN="your-token-here"
```

## Using the CLI

The CLI provides a console-friendly interface for all Data Space operations.

### Installation (for CLI usage)

```bash
pip install -r requirements.txt
```

### CLI Commands

#### Sync Catalog from OpenMetadata

```bash
python src/cli.py sync-catalog --token $DATASPACE_TOKEN
```

#### List Catalog Items

```bash
python src/cli.py list-catalog
```

#### Download Catalog Item

```bash
python src/cli.py download-catalog --catalog-id <id> --output catalog.json
```

#### Publish a Dataset

```bash
python src/cli.py publish \
  --title "Customer Analytics" \
  --description "Customer behavior and demographics" \
  --metadata '{"tags": ["analytics", "customers"]}' \
  --token $DATASPACE_TOKEN
```

#### Create a Data Request

```bash
python src/cli.py request \
  --subject "Need customer data for analysis" \
  --publication-id <publication-id> \
  --token $DATASPACE_TOKEN
```

#### Create a Contract

```bash
python src/cli.py contract \
  --request-id <request-id> \
  --terms '{"duration": "1 year", "usage": "analytics"}' \
  --token $DATASPACE_TOKEN
```

#### Create a Data Transfer

```bash
python src/cli.py transfer \
  --contract-id <contract-id> \
  --token $DATASPACE_TOKEN
```

This returns a presigned URL for downloading the data.

#### View Audit Logs

```bash
python src/cli.py view-audit --limit 50
```

### CLI Environment Variables

```bash
export DATASPACE_API_URL=http://localhost:8000
export DATASPACE_TOKEN=your-jwt-token
```

## Using the REST API

### Curl Examples

#### List Publications

```bash
curl http://localhost:8000/publications
```

#### Create Publication (requires provider role)

```bash
curl -X POST http://localhost:8000/publications \
  -H "Authorization: Bearer $DATASPACE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales Data 2024",
    "description": "Quarterly sales figures",
    "metadata": {"department": "sales"}
  }'
```

#### Create Request (requires consumer role)

```bash
curl -X POST http://localhost:8000/requests \
  -H "Authorization: Bearer $DATASPACE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Request for sales data",
    "publication_id": "<publication-id>"
  }'
```

#### Create Contract

```bash
curl -X POST http://localhost:8000/contracts \
  -H "Authorization: Bearer $DATASPACE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "<request-id>",
    "terms": {"duration": "6 months"}
  }'
```

#### Create Transfer

```bash
curl -X POST http://localhost:8000/transfers \
  -H "Authorization: Bearer $DATASPACE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "<contract-id>",
    "destination": "s3://bucket/path"
  }'
```

#### Sync Catalog

```bash
curl -X POST http://localhost:8000/sync/catalog \
  -H "Authorization: Bearer $DATASPACE_TOKEN"
```

#### View Audit Logs

```bash
curl http://localhost:8000/audit?limit=50 \
  -H "Authorization: Bearer $DATASPACE_TOKEN"
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.local.example`:

```bash
# Database
DATABASE_URL=postgresql://dataspace_user:changeme@db:5432/dataspace

# OpenMetadata
OPENMETADATA_URL=http://openmetadata:8585
OPENMETADATA_API_KEY=

# Keycloak
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=dataspace
KEYCLOAK_CLIENT_ID=dataspace-api
KEYCLOAK_CLIENT_SECRET=dataspace-secret

# MinIO/S3
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=dataspace-transfers
MINIO_USE_SSL=false

# API
LOG_LEVEL=INFO
```

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API (development mode)
uvicorn src.main:app --reload --log-level info
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

## User Roles

The system supports three roles configured in Keycloak:

- **Provider**: Can publish datasets and sync catalogs
- **Consumer**: Can request data and create contracts
- **Broker**: Can facilitate data exchanges (future functionality)

## Audit Trail

Every important operation is logged to:

1. **Console**: INFO-level logs visible during execution
2. **Database**: Persistent append-only `audit_logs` table
3. **API**: `/audit` endpoint for querying logs

Example audit events:
- `publication_created`
- `request_created`
- `contract_created`
- `contract_signed_implicit`
- `transfer_initiated`
- `transfer_completed`
- `catalog_synced`

## Security Features

- JWT-based authentication via Keycloak OIDC
- JWKS token verification
- Role-based access control (RBAC)
- Secure S3 presigned URLs with expiration
- Audit logging for all operations
- Database migrations for schema versioning

## Console Output

All operations produce clear, step-by-step console output:

```
================================================================================
Starting catalog sync by user provider-user
================================================================================
▶ Fetching tables from OpenMetadata (limit: 100)
✓ Successfully fetched 3 tables from OpenMetadata
▶ Processing catalog item: Customer Dataset
✓ Created publication: id=abc-123, title=Customer Dataset
▶ Processing catalog item: Orders Dataset
✓ Created publication: id=def-456, title=Orders Dataset
================================================================================
Catalog sync completed: 2 new publications created
================================================================================
```

## Compliance

This implementation follows:

- **IDSA**: International Data Spaces Architecture principles
- **DSSC**: Data Spaces Support Centre guidelines
- **DCAT**: Data Catalog Vocabulary for metadata
- **ODRL**: Open Digital Rights Language for policies (future)

## Troubleshooting

### Services not starting

```bash
# Check service logs
docker-compose logs <service-name>

# Restart services
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

### OpenMetadata not available

The system will gracefully fall back to mock data if OpenMetadata is not available. Check logs:

```bash
docker-compose logs openmetadata
```

### Authentication errors

Ensure Keycloak is running and the realm is imported:

```bash
docker-compose logs keycloak
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure tests pass: `pytest tests/`
5. Submit a pull request

## License

Apache-2.0

## Support

For issues and questions:
- GitHub Issues: https://github.com/yisus189/data-space-inetum/issues
- Documentation: See `/docs` directory

## Roadmap

- [ ] ODRL policy enforcement
- [ ] Data usage control
- [ ] Blockchain-based audit trail
- [ ] Multi-tenancy support
- [ ] Advanced catalog search
- [ ] Data quality metrics
- [ ] Real-time notifications