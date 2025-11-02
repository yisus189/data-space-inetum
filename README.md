# Data Space - Enterprise Data Sharing Platform

A complete, console-first Data Space implementation following IDSA (International Data Spaces Association) and DSSC (Data Spaces Support Centre) principles. This platform enables secure, auditable data sharing between organizations with built-in catalog integration, authentication, and transfer management.

## Features

- 🔐 **Authentication & Authorization**: Keycloak-based OIDC with role-based access control (Provider, Consumer, Broker)
- 📊 **Catalog Integration**: Automatic synchronization with OpenMetadata (with mock data fallback)
- 📝 **Data Publications**: Providers can publish datasets with metadata
- 🤝 **Access Requests**: Consumers can request access to published data
- 📄 **Smart Contracts**: Automated contract generation with implicit digital signatures
- 🚀 **Data Transfers**: Secure S3 presigned URLs for data transfer via MinIO
- 📜 **Audit Logging**: Comprehensive, append-only audit trail for all operations
- 🖥️ **CLI Tool**: Command-line interface for all major operations
- 🔌 **REST API**: Full OpenAPI/Swagger documentation
- 🐳 **Docker Support**: Complete containerized deployment

## Architecture

```
┌─────────────┐
│   Client    │
│  (CLI/API)  │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│          FastAPI Application                │
│  ┌────────────────────────────────────┐    │
│  │  Authentication (Keycloak OIDC)    │    │
│  └────────────────────────────────────┘    │
│  ┌────────────────────────────────────┐    │
│  │  API Routers (RBAC Protected)      │    │
│  │  • Publications  • Requests         │    │
│  │  • Contracts    • Transfers        │    │
│  │  • Catalog      • Audit            │    │
│  └────────────────────────────────────┘    │
└──────┬────────────┬────────────┬───────────┘
       │            │            │
┌──────▼──────┐ ┌──▼────────┐ ┌─▼──────────┐
│  PostgreSQL │ │  MinIO    │ │OpenMetadata│
│  (Database) │ │  (S3)     │ │ (Catalog)  │
└─────────────┘ └───────────┘ └────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Git

### 1. Clone and Setup

```bash
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Copy environment template
cp .env.local.example .env.local
```

### 2. Start Services

```bash
# Start all services (Postgres, Keycloak, MinIO, OpenMetadata, API)
docker-compose up -d

# Wait for services to be ready (~2-3 minutes)
# Check logs
docker-compose logs -f api
```

### 3. Verify Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Keycloak**: http://localhost:8080 (admin: kc-admin / changeMeAdmin123!)
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin123)
- **OpenMetadata**: http://localhost:8585

## Development Credentials

⚠️ **For development only - NEVER use in production!**

### Keycloak Users

| Username   | Password     | Role     | Purpose                    |
|------------|--------------|----------|----------------------------|
| provider1  | provider123  | provider | Publish datasets           |
| consumer1  | consumer123  | consumer | Request & consume data     |
| broker1    | broker123    | broker   | Admin/orchestrator         |

### Service Credentials

- **Keycloak Admin**: kc-admin / changeMeAdmin123!
- **Keycloak Client Secret**: dataspace-client-secret
- **PostgreSQL**: dataspace_user / changeme
- **MinIO**: minioadmin / minioadmin123

## Usage Examples

### Using the CLI

#### 1. Login and Get Token

```bash
python -m src.cli login --username provider1 --password provider123

# Copy the access token from output
export TOKEN="<your-access-token>"
```

#### 2. Sync Catalog from OpenMetadata

```bash
# As broker
python -m src.cli --token $TOKEN sync-catalog
```

#### 3. Create a Publication (as Provider)

```bash
python -m src.cli --token $TOKEN publish \
  --title "Customer Dataset" \
  --description "Customer information and metrics" \
  --s3-path "datasets/customers.parquet"
```

#### 4. List Catalog

```bash
python -m src.cli --token $TOKEN list-catalog
```

#### 5. Request Access (as Consumer)

```bash
# Get token as consumer
python -m src.cli login --username consumer1 --password consumer123
export CONSUMER_TOKEN="<consumer-token>"

# Create request
python -m src.cli --token $CONSUMER_TOKEN request \
  --publication-id 1 \
  --subject "Access for analytics" \
  --message "Need access for quarterly analysis"
```

#### 6. Create Contract (as Provider)

```bash
# After approving the request in the system
python -m src.cli --token $TOKEN contract-create --request-id 1
```

#### 7. Initiate Transfer (as Consumer)

```bash
python -m src.cli --token $CONSUMER_TOKEN transfer \
  --contract-id 1 \
  --destination "analytics/incoming/"
```

#### 8. View Audit Logs

```bash
python -m src.cli --token $TOKEN view-audit --limit 50
```

### Using the API Directly

#### 1. Get Access Token

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "username": "provider1",
    "password": "provider123"
  }'
```

#### 2. Create Publication

```bash
curl -X POST http://localhost:8000/publications \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales Data Q4 2024",
    "description": "Quarterly sales figures",
    "metadata": {
      "department": "sales",
      "quarter": "Q4",
      "year": 2024
    },
    "s3_path": "data/sales_q4_2024.csv"
  }'
```

#### 3. List Publications

```bash
curl -X GET http://localhost:8000/publications \
  -H "Authorization: Bearer <token>"
```

#### 4. Interactive API Documentation

Visit http://localhost:8000/docs for full interactive API documentation with try-it-out functionality.

## Complete Workflow Example

### Scenario: Provider shares dataset with Consumer

1. **Provider publishes dataset**:
   ```bash
   # Login as provider
   TOKEN=$(python -m src.cli login --username provider1 --password provider123 | grep "Access Token:" | cut -d' ' -f4)
   
   # Publish dataset
   python -m src.cli --token $TOKEN publish \
     --title "Product Inventory" \
     --description "Current product stock levels" \
     --s3-path "inventory/products.parquet"
   ```

2. **Consumer browses catalog and requests access**:
   ```bash
   # Login as consumer
   CTOKEN=$(python -m src.cli login --username consumer1 --password consumer123 | grep "Access Token:" | cut -d' ' -f4)
   
   # View catalog
   python -m src.cli --token $CTOKEN list-catalog
   
   # Request access to publication ID 1
   python -m src.cli --token $CTOKEN request \
     --publication-id 1 \
     --subject "Inventory analysis access" \
     --message "Need data for supply chain optimization"
   ```

3. **Provider approves and creates contract** (via API):
   ```bash
   # Update request status to approved
   curl -X PATCH http://localhost:8000/requests/1 \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "status": "approved",
       "response_message": "Approved for business use"
     }'
   
   # Create contract
   python -m src.cli --token $TOKEN contract-create --request-id 1
   ```

4. **Consumer initiates data transfer**:
   ```bash
   # Initiate transfer - receives presigned URL
   python -m src.cli --token $CTOKEN transfer --contract-id 1
   
   # Use the presigned URL to download data
   curl -o data.parquet "<presigned-url-from-output>"
   ```

5. **View audit trail**:
   ```bash
   # As broker, view all activity
   BTOKEN=$(python -m src.cli login --username broker1 --password broker123 | grep "Access Token:" | cut -d' ' -f4)
   python -m src.cli --token $BTOKEN view-audit --limit 100
   ```

## Database Migrations

```bash
# Run migrations (happens automatically in Docker)
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Rollback
alembic downgrade -1
```

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

## Project Structure

```
data-space-inetum/
├── src/
│   ├── auth/              # Authentication & authorization
│   │   ├── keycloak.py   # Keycloak OIDC integration
│   │   └── dependencies.py # FastAPI auth dependencies
│   ├── catalog/          # OpenMetadata integration
│   │   └── sync.py       # Catalog synchronization
│   ├── db/               # Database layer
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── repositories.py # Data access layer
│   │   └── session.py    # DB connection management
│   ├── routers/          # API endpoints
│   │   ├── publications.py
│   │   ├── requests.py
│   │   ├── contracts.py
│   │   ├── transfers.py
│   │   ├── catalog.py
│   │   ├── audit.py
│   │   └── auth.py
│   ├── transfer/         # Transfer management
│   │   └── s3.py         # S3/MinIO operations
│   ├── cli.py            # Command-line interface
│   ├── main.py           # FastAPI application
│   └── schemas.py        # Pydantic schemas
├── alembic/              # Database migrations
├── infra/                # Infrastructure config
│   ├── keycloak/
│   │   └── realm-export.json
│   └── docker-compose.override.yml
├── tests/                # Test suite
├── docker-compose.yml    # Service orchestration
├── Dockerfile            # API container
├── requirements.txt      # Python dependencies
└── README.md

```

## API Endpoints

### Authentication
- `POST /auth/token` - Get access token

### Publications
- `GET /publications` - List publications
- `POST /publications` - Create publication (provider)
- `GET /publications/{id}` - Get publication details

### Requests
- `GET /requests` - List requests
- `POST /requests` - Create access request (consumer)
- `GET /requests/{id}` - Get request details
- `PATCH /requests/{id}` - Update request status (provider)

### Contracts
- `GET /contracts` - List contracts
- `POST /contracts` - Create contract (provider)
- `GET /contracts/{id}` - Get contract details

### Transfers
- `GET /transfers` - List transfers
- `POST /transfers` - Initiate transfer (consumer)
- `GET /transfers/{id}` - Get transfer details

### Catalog
- `POST /catalog/sync` - Sync from OpenMetadata (broker)
- `GET /catalog` - List catalog items
- `GET /catalog/{id}` - Get catalog item
- `GET /catalog/{id}/download` - Download metadata JSON

### Audit
- `GET /audit` - List audit logs
- `GET /audit/my` - List current user's audit logs

## Security Notes

### Development vs Production

This setup includes development credentials for ease of use. **Before deploying to production**:

1. **Change all passwords and secrets**
2. **Use proper SSL/TLS certificates**
3. **Configure proper CORS policies**
4. **Set up network firewalls**
5. **Enable Keycloak production mode**
6. **Use external secret management** (e.g., HashiCorp Vault)
7. **Review and harden database access**
8. **Set up proper backup procedures**
9. **Implement rate limiting**
10. **Add monitoring and alerting**

### Current Security Features

- ✅ JWT-based authentication via Keycloak
- ✅ Role-based access control (RBAC)
- ✅ Append-only audit logging
- ✅ Presigned URLs for time-limited data access
- ✅ Input validation with Pydantic
- ✅ SQL injection protection via SQLAlchemy ORM
- ✅ Automatic contract expiration support

## Troubleshooting

### Services won't start

```bash
# Check service logs
docker-compose logs -f

# Restart specific service
docker-compose restart api

# Full restart
docker-compose down
docker-compose up -d
```

### Database connection errors

```bash
# Check if database is ready
docker-compose logs db | grep "database system is ready"

# Manually run migrations
docker-compose exec api alembic upgrade head
```

### Keycloak not accessible

```bash
# Wait for Keycloak to fully start (can take 2-3 minutes)
docker-compose logs -f keycloak

# Check if realm was imported
docker-compose exec keycloak /opt/keycloak/bin/kc.sh show realms
```

### OpenMetadata unavailable

The system automatically falls back to mock catalog data if OpenMetadata is unavailable. Check logs:

```bash
docker-compose logs api | grep "OpenMetadata"
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yisus189/data-space-inetum/issues
- Documentation: See `/docs` directory

## Acknowledgments

- Built following IDSA and DSSC principles
- Integrates with OpenMetadata for catalog management
- Uses Keycloak for enterprise-grade authentication
- Inspired by international data space initiatives