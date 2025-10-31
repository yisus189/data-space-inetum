# Data Space Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Users / Clients                          │
│  (Provider, Consumer, Broker)                                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ HTTPS/REST
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                     Data Space API                               │
│                      (FastAPI)                                   │
│                                                                  │
│  Endpoints:                                                      │
│  • /publications - CRUD operations                              │
│  • /requests     - Data access requests                         │
│  • /contracts    - Agreement management                         │
│  • /transfers    - Data transfer initiation                     │
│  • /catalog      - Catalog browsing                             │
│  • /audit        - Audit log queries                            │
│  • /sync/catalog - OpenMetadata sync                            │
└──────┬─────────┬────────────┬──────────┬──────────┬─────────────┘
       │         │            │          │          │
       │         │            │          │          │
       ▼         ▼            ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
│PostgreSQL│ │Keycloak │ │ MinIO  │ │OpenMeta│ │  External   │
│  (DB)    │ │(Auth)   │ │ (S3)   │ │ data   │ │  Systems    │
└──────────┘ └─────────┘ └────────┘ └────────┘ └─────────────┘
```

## Component Details

### 1. Data Space API (FastAPI)

**Responsibilities:**
- Expose REST API endpoints
- Authenticate and authorize requests
- Orchestrate business logic
- Manage data flow between components

**Key Modules:**
- `src/main.py` - Application entry point
- `src/app/` - Business logic (schemas, audit, transfers)
- `src/db/` - Database models and configuration
- `src/auth/` - Authentication/authorization
- `src/catalog/` - OpenMetadata integration

### 2. PostgreSQL Database

**Purpose:** Primary data store

**Tables:**
- `participants` - Users/organizations
- `roles` - User role assignments
- `publications` - Data offerings
- `requests` - Access requests
- `contracts` - Data usage agreements
- `transfers` - Transfer records
- `audit_logs` - Immutable audit trail

### 3. Keycloak

**Purpose:** Identity and Access Management

**Features:**
- OIDC/OAuth2 authentication
- JWT token issuance
- User management
- Role-based access control

**Roles:**
- `provider` - Can publish data
- `consumer` - Can request and consume data
- `broker` - Can intermediate transactions

### 4. MinIO

**Purpose:** S3-compatible object storage

**Usage:**
- Store transferred data
- Generate presigned URLs
- Secure file access
- Support for large files

### 5. OpenMetadata

**Purpose:** Data catalog and metadata management

**Integration:**
- Table/dataset metadata
- Schema information
- Data lineage
- Tags and ownership

## Data Flow

### Publication Flow

```
Provider → [Auth] → Create Publication → DB → Audit Log
```

### Request & Contract Flow

```
Consumer → [Auth] → Create Request → DB → Audit Log
                                      ↓
Provider → [Auth] → Review Request → Create Contract → DB → Audit Log
```

### Transfer Flow

```
Consumer → [Auth] → Request Transfer → Validate Contract
                                      ↓
                                   Generate Presigned URL (MinIO)
                                      ↓
                                   Create Transfer Record → DB → Audit Log
                                      ↓
Consumer ← Return Presigned URL ← Complete
```

### Catalog Sync Flow

```
Provider → [Auth] → Trigger Sync → OpenMetadata API
                                      ↓
                                   Fetch Tables/Datasets
                                      ↓
                                   Map to Publications
                                      ↓
                                   Upsert DB → Audit Log
```

## Security Architecture

### Authentication Flow

```
Client → Request with credentials → Keycloak
                                      ↓
                                   Validate Credentials
                                      ↓
                                   Generate JWT
                                      ↓
Client ← JWT Token ← Keycloak
       │
       └→ API Request with JWT → API
                                  ↓
                              Verify JWT (JWKS)
                                  ↓
                              Extract roles
                                  ↓
                              Authorize
                                  ↓
                              Process Request
```

### Authorization Model

**Role Hierarchy:**
```
broker (highest privileges)
  └── Can perform all operations
      
provider
  └── Can create publications
  └── Can sign contracts
  └── Can sync catalog
      
consumer
  └── Can create requests
  └── Can initiate transfers
```

## Audit Trail

All operations are logged with:
- Event type
- User ID
- Resource type and ID
- Timestamp
- IP address (optional)
- User agent (optional)
- Payload details

**Audit Events:**
- `publication_created`
- `request_created`
- `contract_created`
- `contract_signed`
- `transfer_initiated`
- `transfer_completed`
- `catalog_synced`

## Scalability Considerations

### Horizontal Scaling
- API: Multiple instances behind load balancer
- Database: Read replicas for queries
- MinIO: Distributed mode for large-scale storage

### Performance Optimization
- Database indexes on frequently queried fields
- JWKS caching (5-minute TTL)
- Connection pooling for database
- Async operations where appropriate

### Monitoring Points
- API response times
- Database query performance
- Authentication success/failure rates
- Transfer success rates
- Audit log growth rate

## Deployment Architecture

### Development
```
Docker Compose
  ├── db (PostgreSQL)
  ├── keycloak
  ├── minio
  ├── openmetadata-db
  ├── openmetadata
  ├── migrations
  └── api
```

### Production Considerations
- Use managed database (AWS RDS, Azure Database)
- Use managed object storage (AWS S3, Azure Blob)
- Use managed Keycloak or auth service
- Deploy API on Kubernetes
- Enable SSL/TLS everywhere
- Set up monitoring and alerting
- Implement backup and disaster recovery

## IDSA/DSSC Compliance

### Implemented Controls

**Data Sovereignty:**
- Contracts define usage terms
- Audit trail for accountability
- Access control enforcement

**Interoperability:**
- REST API with OpenAPI documentation
- Standard authentication (OIDC)
- JSON data formats

**Trust & Security:**
- Authentication required
- Role-based authorization
- Encrypted transfers (presigned URLs)
- Immutable audit logs

**Metadata Management:**
- OpenMetadata integration
- Schema and lineage tracking
- Searchable catalog

### Future Enhancements
- [ ] Policy enforcement engine (ODRL)
- [ ] Data usage tracking
- [ ] Consent management
- [ ] Cross-space federation
- [ ] Advanced contract templates
