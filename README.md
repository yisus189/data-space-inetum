# Data Space - Production-Grade IDSA & DSSC Compliant Implementation

A complete production-like Data Space implementation optimized for console operations, following IDSA (International Data Spaces Association) and DSSC (Data Spaces Support Centre) principles.

## Overview

This Data Space provides a comprehensive solution for secure data sharing and exchange between organizations. It includes:

- **Data Catalog Management**: Publish and discover datasets with OpenMetadata integration
- **Access Request Workflow**: Request, approve, and manage data access
- **Contract Management**: Automated contract creation with implicit digital signatures
- **Secure Transfers**: S3-based data transfers with presigned URLs
- **Complete Audit Trail**: Immutable audit logs for all operations
- **Role-Based Access Control**: Provider, Consumer, and Broker roles via Keycloak
- **CLI & API**: Both programmatic and command-line interfaces

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Space API                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Publications│ │ Requests │ │Contracts │ │Transfers │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐                                │
│  │ Catalog  │  │  Audit   │                                │
│  └──────────┘  └──────────┘                                │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
    ┌────▼────┐    ┌───▼────┐    ┌───▼─────┐   ┌───▼──────┐
    │Keycloak │    │Postgres│    │  MinIO  │   │OpenMetadata│
    │ (Auth)  │    │  (DB)  │    │  (S3)   │   │ (Catalog) │
    └─────────┘    └────────┘    └─────────┘   └───────────┘
```

## Features

### 1. Publications & Catalog
- Publish datasets with metadata, schema, and access policies
- Sync catalog from OpenMetadata (with mock fallback)
- Browse and search available datasets
- Download catalog metadata as JSON

### 2. Access Requests
- Submit access requests for datasets
- Purpose and intended use documentation
- Provider approval workflow
- Request status tracking

### 3. Contracts
- Automatic contract generation from approved requests
- Implicit digital signatures with SHA256 hashing
- Contract lifecycle management (active, expired, terminated)
- Terms and policies enforcement

### 4. Data Transfers
- S3 presigned URL generation for secure downloads
- MinIO support for local development
- Transfer progress tracking
- Automatic audit logging

### 5. Authentication & Authorization
- Keycloak OIDC integration with JWKS validation
- Three roles: Provider, Consumer, Broker
- Fine-grained endpoint protection
- JWT-based authentication

### 6. Audit System
- Append-only audit logs
- All operations logged automatically
- Console and database logging
- Queryable audit trail

### 7. Command-Line Interface
- Full-featured CLI for all operations
- Step-by-step console output
- Authentication token support
- Production-ready scripts

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- 8GB RAM recommended

### 1. Clone and Setup

```bash
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Copy environment configuration
cp .env.local.example .env.local
```

### 2. Start the Stack

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Keycloak**: http://localhost:8080
- **MinIO Console**: http://localhost:9001
- **OpenMetadata**: http://localhost:8585

### 3. Get Authentication Token

The stack includes pre-configured users:

**Provider User:**
```bash
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-client" \
  -d "client_secret=dataspace-client-secret" \
  -d "grant_type=password" \
  -d "username=provider-user" \
  -d "password=provider123" | jq -r '.access_token'
```

**Consumer User:**
```bash
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-client" \
  -d "client_secret=dataspace-client-secret" \
  -d "grant_type=password" \
  -d "username=consumer-user" \
  -d "password=consumer123" | jq -r '.access_token'
```

**Broker User:**
```bash
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-client" \
  -d "client_secret=dataspace-client-secret" \
  -d "grant_type=password" \
  -d "username=broker-user" \
  -d "password=broker123" | jq -r '.access_token'
```

Save the token to use in subsequent requests:
```bash
export API_TOKEN="<your-token-here>"
```

### 4. Using the API

**Explore the API:**
Visit http://localhost:8000/docs for interactive API documentation.

**Create a Publication (as Provider):**
```bash
curl -X POST "http://localhost:8000/publications" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Customer Dataset",
    "description": "Customer master data",
    "tags": ["customers", "pii"],
    "data_location": "s3://my-bucket/customers"
  }'
```

**List Publications:**
```bash
curl -X GET "http://localhost:8000/publications" \
  -H "Authorization: Bearer $API_TOKEN"
```

### 5. Using the CLI

**Install CLI dependencies:**
```bash
pip install -r requirements.txt
```

**Set environment variables:**
```bash
export API_URL="http://localhost:8000"
export API_TOKEN="<your-token>"
```

**Publish a dataset:**
```bash
python src/cli.py publish \
  --title "Sales Data 2024" \
  --description "Annual sales figures" \
  --tags "sales,analytics"
```

**Sync catalog from OpenMetadata:**
```bash
python src/cli.py sync-catalog
```

**List catalog items:**
```bash
python src/cli.py list-catalog --limit 10
```

**Request access to a dataset:**
```bash
python src/cli.py request \
  --publication-id "<publication-id>" \
  --subject "Need access for analysis" \
  --purpose "Market research"
```

**View audit logs (as Broker):**
```bash
python src/cli.py view-audit --limit 20
```

## Complete Workflow Example

### As a Data Provider

1. **Sync catalog** from OpenMetadata:
```bash
python src/cli.py sync-catalog
```

2. **Manually publish** additional datasets:
```bash
python src/cli.py publish \
  --title "Q4 Revenue Report" \
  --description "Quarterly revenue breakdown" \
  --tags "finance,quarterly"
```

3. **List publications** to verify:
```bash
python src/cli.py list-publications
```

### As a Data Consumer

1. **Browse catalog**:
```bash
python src/cli.py list-catalog
```

2. **Request access**:
```bash
python src/cli.py request \
  --publication-id "<pub-id>" \
  --subject "Data analysis request" \
  --purpose "Business intelligence" \
  --intended-use "Dashboard creation"
```

3. **Check request status**:
```bash
python src/cli.py list-requests
```

### As a Data Provider (Approval)

1. **View incoming requests** via API:
```bash
curl -X GET "http://localhost:8000/requests?status_filter=OPEN" \
  -H "Authorization: Bearer $API_TOKEN"
```

2. **Approve request**:
```bash
curl -X PUT "http://localhost:8000/requests/<request-id>" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "APPROVED", "response_notes": "Approved for 30 days"}'
```

3. **Create contract**:
```bash
python src/cli.py contract-create \
  --request-id "<request-id>" \
  --end-date "2024-12-31"
```

### As a Data Consumer (Transfer)

1. **List active contracts**:
```bash
python src/cli.py list-contracts
```

2. **Initiate transfer**:
```bash
python src/cli.py transfer \
  --contract-id "<contract-id>" \
  --destination "my-local-storage" \
  --format "json"
```

3. **Download using presigned URL** (from transfer response).

## Development

### Running Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://dataspace_user:changeme@localhost:5432/dataspace"
export KEYCLOAK_URL="http://localhost:8080"
export MINIO_ENDPOINT="localhost:9000"

# Run migrations
alembic upgrade head

# Start API
uvicorn src.main:app --reload
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://dataspace_user:changeme@localhost:5432/dataspace` |
| `KEYCLOAK_URL` | Keycloak server URL | `http://localhost:8080` |
| `KEYCLOAK_REALM` | Keycloak realm name | `dataspace` |
| `KEYCLOAK_CLIENT_ID` | OAuth2 client ID | `dataspace-client` |
| `KEYCLOAK_CLIENT_SECRET` | OAuth2 client secret | `dataspace-client-secret` |
| `MINIO_ENDPOINT` | MinIO endpoint | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin123` |
| `MINIO_BUCKET` | S3 bucket name | `dataspace-transfers` |
| `OPENMETADATA_URL` | OpenMetadata URL | `http://localhost:8585` |
| `API_HOST` | API host | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Default Users

| Role | Username | Password | Permissions |
|------|----------|----------|-------------|
| Provider | `provider-user` | `provider123` | Publish datasets, approve requests |
| Consumer | `consumer-user` | `consumer123` | Request data, initiate transfers |
| Broker | `broker-user` | `broker123` | Full administrative access |

### Keycloak Admin

- **Admin User**: `kc-admin`
- **Admin Password**: `changeMeAdmin123!`
- **Console**: http://localhost:8080

## Security Considerations

⚠️ **Important**: This implementation is optimized for development and demonstration. Before production use:

1. **Change all default passwords and secrets**
2. **Configure SSL/TLS** for all services
3. **Review and update** Keycloak realm configuration
4. **Enable proper firewall** rules
5. **Configure backup** strategies
6. **Review audit logs** regularly
7. **Update dependencies** to latest secure versions
8. **Implement proper secret management** (e.g., Vault)

## API Documentation

Full API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

### Main Endpoints

- `POST /publications` - Create publication
- `GET /publications` - List publications
- `POST /requests` - Create access request
- `PUT /requests/{id}` - Approve/reject request
- `POST /contracts` - Create contract
- `POST /transfers` - Initiate transfer
- `POST /catalog/sync` - Sync from OpenMetadata
- `GET /catalog` - Browse catalog
- `GET /audit` - View audit logs

## Troubleshooting

### Services not starting

```bash
# Check logs
docker-compose logs

# Restart specific service
docker-compose restart api

# Rebuild and restart
docker-compose up --build -d
```

### Database connection issues

```bash
# Check database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Connect to database
docker-compose exec db psql -U dataspace_user -d dataspace
```

### Authentication issues

```bash
# Check Keycloak is running
docker-compose ps keycloak

# Access Keycloak admin console
# http://localhost:8080 (admin/admin)

# Verify realm import
docker-compose logs keycloak | grep "realm-export"
```

### OpenMetadata not available

The system will automatically use mock data when OpenMetadata is unreachable. Check logs for:
```
Using mock catalog data
```

## License

Apache License 2.0

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/yisus189/data-space-inetum/issues
- Documentation: http://localhost:8000/docs (when running locally)

## Acknowledgments

This implementation follows guidelines from:
- IDSA (International Data Spaces Association)
- DSSC (Data Spaces Support Centre)
- OpenMetadata for data catalog functionality