# Data Space conforme IDSA & DSSC

**Complete production-ready Data Space implementation with PostgreSQL persistence, Keycloak authentication, OpenMetadata integration, and S3 transfers.**

## Overview

This project implements a comprehensive Data Space following IDSA (International Data Spaces Association) and DSSC (Data Spaces Support Centre) principles. It provides:

- **Publication of datasets** with metadata management
- **Request/response workflows** for data access
- **Contract management** with implicit digital signatures
- **Secure data transfers** using S3 pre-signed URLs
- **Real-time catalog synchronization** with OpenMetadata
- **Authentication & Authorization** via Keycloak (OIDC/OAuth2)
- **Role-Based Access Control (RBAC)** with provider, consumer, and broker roles
- **Comprehensive audit logging** for compliance and traceability
- **PostgreSQL persistence** with Alembic migrations
- **MinIO/S3 support** for data transfers

## Architecture

### Components

- **API (FastAPI)**: REST API with OpenAPI documentation
- **Database (PostgreSQL)**: Persistent storage for all entities
- **Keycloak**: Identity and Access Management (IAM) with OIDC
- **MinIO**: S3-compatible object storage for local development
- **OpenMetadata**: Data catalog integration (optional, uses mocks if not configured)

### Data Model

```
User (provider/consumer/broker)
  ↓
Publication (datasets/catalog items)
  ↓
Request (data access requests)
  ↓
Contract (signed agreements with terms)
  ↓
Transfer (data transfer with pre-signed URLs)
  ↓
AuditLog (immutable audit trail)
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yisus189/data-space-inetum.git
   cd data-space-inetum
   ```

2. **Start all services**:
   ```bash
   docker-compose up --build
   ```

3. **Access the services**:
   - **API**: http://localhost:8000
   - **API Docs (Swagger)**: http://localhost:8000/docs
   - **Keycloak Admin**: http://localhost:8080 (admin/admin)
   - **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### Authentication

The system uses Keycloak for authentication. Test users are pre-configured:

| Username | Password | Role |
|----------|----------|------|
| provider-user | provider123 | provider |
| consumer-user | consumer123 | consumer |
| broker-user | broker123 | broker |

#### Getting an Access Token

```bash
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" \
  -d "grant_type=password" \
  -d "username=provider-user" \
  -d "password=provider123"
```

Use the returned `access_token` in API requests:

```bash
curl -X GET "http://localhost:8000/publications" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://dataspace_user:changeme@db:5432/dataspace` |
| `KEYCLOAK_SERVER_URL` | Keycloak server URL | `http://keycloak:8080` |
| `KEYCLOAK_REALM` | Keycloak realm name | `dataspace` |
| `KEYCLOAK_CLIENT_ID` | Keycloak client ID | `dataspace-api` |
| `KEYCLOAK_CLIENT_SECRET` | Keycloak client secret | `dataspace-secret` |
| `S3_ENDPOINT_URL` | S3/MinIO endpoint | `http://minio:9000` |
| `S3_ACCESS_KEY` | S3 access key | `minioadmin` |
| `S3_SECRET_KEY` | S3 secret key | `minioadmin` |
| `S3_BUCKET` | S3 bucket for transfers | `dataspace-transfers` |

### Optional Variables

| Variable | Description |
|----------|-------------|
| `OPENMETADATA_URL` | OpenMetadata server URL (uses mocks if not set) |
| `OPENMETADATA_API_KEY` | OpenMetadata API key |
| `AUDIT_WEBHOOK_URL` | Webhook URL for audit log anchoring |

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

### Publications (Provider role required)
- `POST /publications` - Create a new publication
- `GET /publications` - List all publications
- `GET /publications/{id}` - Get specific publication

### Requests (Consumer role required)
- `POST /requests` - Create a data access request
- `GET /requests` - List all requests
- `GET /requests/{id}` - Get specific request

### Contracts
- `POST /contracts` - Create contract from request
- `GET /contracts` - List all contracts
- `GET /contracts/{id}` - Get specific contract

### Transfers
- `POST /transfers` - Create transfer with pre-signed URL
- `GET /transfers` - List all transfers
- `GET /transfers/{id}` - Get specific transfer
- `POST /transfers/{id}/complete` - Mark transfer as completed

### Catalog Synchronization (Provider role required)
- `POST /sync/catalog` - Sync catalog from OpenMetadata

### Audit Logs
- `GET /audit-logs` - List audit logs (recent first)

## Complete Workflow Example

### 1. Authenticate as Provider

```bash
TOKEN=$(curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" \
  -d "grant_type=password" \
  -d "username=provider-user" \
  -d "password=provider123" | jq -r '.access_token')
```

### 2. Create a Publication

```bash
PUB_ID=$(curl -X POST "http://localhost:8000/publications" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Customer Dataset",
    "description": "Customer information dataset",
    "metadata": {
      "schema": {
        "fields": [
          {"name": "id", "type": "int"},
          {"name": "name", "type": "string"},
          {"name": "email", "type": "string"}
        ]
      }
    }
  }' | jq -r '.id')
```

### 3. Authenticate as Consumer

```bash
CONSUMER_TOKEN=$(curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" \
  -d "grant_type=password" \
  -d "username=consumer-user" \
  -d "password=consumer123" | jq -r '.access_token')
```

### 4. Create a Request

```bash
REQ_ID=$(curl -X POST "http://localhost:8000/requests" \
  -H "Authorization: Bearer $CONSUMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"subject\": \"Request access to customer data\",
    \"publication_id\": \"$PUB_ID\"
  }" | jq -r '.id')
```

### 5. Create a Contract

```bash
CONTRACT_ID=$(curl -X POST "http://localhost:8000/contracts" \
  -H "Authorization: Bearer $CONSUMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"request_id\": \"$REQ_ID\",
    \"terms\": {
      \"duration\": \"1 year\",
      \"usage\": \"analytics only\",
      \"restrictions\": \"no redistribution\"
    }
  }" | jq -r '.id')
```

### 6. Initiate a Transfer

```bash
TRANSFER=$(curl -X POST "http://localhost:8000/transfers" \
  -H "Authorization: Bearer $CONSUMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contract_id\": \"$CONTRACT_ID\",
    \"destination\": \"customer-data.csv\"
  }")

echo $TRANSFER | jq '.'
```

The response includes a `presigned_url` that can be used to upload data to S3.

### 7. Upload Data (using the pre-signed URL)

```bash
PRESIGNED_URL=$(echo $TRANSFER | jq -r '.presigned_url')

curl -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: text/csv" \
  --data-binary "@sample-data.csv"
```

### 8. Complete the Transfer

```bash
TRANSFER_ID=$(echo $TRANSFER | jq -r '.id')

curl -X POST "http://localhost:8000/transfers/$TRANSFER_ID/complete" \
  -H "Authorization: Bearer $CONSUMER_TOKEN"
```

## Development

### Local Setup

1. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Set up database**:
   ```bash
   # Start only PostgreSQL
   docker-compose up -d db
   
   # Run migrations
   alembic upgrade head
   ```

3. **Run the API locally**:
   ```bash
   uvicorn src.main:app --reload
   ```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback one migration:
```bash
alembic downgrade -1
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

## OpenMetadata Integration

### With Real OpenMetadata Instance

Set environment variables:
```bash
OPENMETADATA_URL=http://your-openmetadata-instance:8585
OPENMETADATA_API_KEY=your-api-key
```

Sync catalog:
```bash
curl -X POST "http://localhost:8000/sync/catalog" \
  -H "Authorization: Bearer $TOKEN"
```

### Without OpenMetadata (Development Mode)

If `OPENMETADATA_URL` is not set, the system uses mock data with sample datasets:
- `customers` - Customer dataset
- `orders` - Orders dataset
- `products` - Products dataset

## S3/MinIO Configuration

### Using MinIO (Local Development)

MinIO is configured in `docker-compose.yml` and starts automatically. Access the console at http://localhost:9001.

### Using AWS S3 (Production)

Update environment variables:
```bash
S3_ENDPOINT_URL=  # Leave empty for AWS S3
S3_ACCESS_KEY=your-aws-access-key
S3_SECRET_KEY=your-aws-secret-key
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
```

## Security

### Authentication & Authorization

- **OIDC/OAuth2** via Keycloak
- **JWT tokens** for API authentication
- **Role-Based Access Control (RBAC)**:
  - `provider`: Can create publications, sync catalog
  - `consumer`: Can create requests, contracts, transfers
  - `broker`: Can mediate transactions

### Audit Logging

All operations are logged in the `audit_logs` table with:
- Event type
- Payload (operation details)
- User ID
- Timestamp

Audit logs are **append-only** and immutable.

### Data Transfer Security

- **Pre-signed URLs** with time-based expiration (1 hour default)
- **Contract validation** before transfer initiation
- **Transfer state tracking** for accountability

## Extending to IDS Connectors

The current implementation uses S3 pre-signed URLs. To extend to IDS connectors:

1. **Implement IDS connector interface** in `src/connectors/ids_connector.py`
2. **Add connector type** to Transfer model
3. **Update transfer endpoint** to support multiple connector types
4. **Configure IDS connector** settings in environment variables

Example structure:
```python
class IDSConnector:
    def initiate_transfer(self, contract_id: str, destination: str) -> str:
        # Implement IDS-specific transfer logic
        pass
```

## Production Deployment

### Considerations

1. **Database**: Use managed PostgreSQL (AWS RDS, Azure Database, etc.)
2. **Keycloak**: Deploy in HA mode with external database
3. **S3**: Use AWS S3 or equivalent with proper IAM roles
4. **HTTPS**: Use reverse proxy (nginx, Traefik) with SSL certificates
5. **Monitoring**: Add Prometheus metrics and Grafana dashboards
6. **Secrets**: Use secret management (AWS Secrets Manager, Vault)

### Docker Compose for Production

See `docker-compose.prod.yml` (to be created) for production configuration.

## Compliance & Standards

- **IDSA**: International Data Spaces Association principles
- **DSSC**: Data Spaces Support Centre guidelines
- **GDPR**: Audit logging for compliance
- **OAuth2/OIDC**: Standard authentication protocols

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

See LICENSE file.

## Support

For issues and questions, please use the GitHub issue tracker.

## Acknowledgments

- IDSA for Data Spaces architecture guidance
- OpenMetadata for catalog management
- Keycloak for identity management