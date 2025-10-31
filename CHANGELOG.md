# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-31

### Added

#### Infrastructure
- Complete Docker Compose setup with Postgres, Keycloak, MinIO, and OpenMetadata
- Dockerfile for API service with production-ready configuration
- Python project setup with pyproject.toml and all dependencies
- Alembic for database migrations with initial schema
- Health check endpoints for all services
- Makefile for common development tasks
- Quick start script for easy setup

#### Database
- SQLAlchemy models: Publication, Request, Contract, Transfer, AuditLog, Participant, Role
- PostgreSQL as primary database
- Complete relationship mapping between entities
- Indexes for performance optimization
- Append-only audit log table

#### Authentication & Authorization
- Keycloak integration for OIDC/JWT authentication
- JWKS-based token verification
- Role-based access control (provider, consumer, broker)
- Pre-configured realm with test users
- Middleware for authentication and role checking

#### API Endpoints
- **Publications**: CRUD operations for data publications
- **Requests**: Create and manage data access requests
- **Contracts**: Sign and manage data usage agreements
- **Transfers**: Initiate data transfers with presigned URLs
- **Audit**: Query audit logs with filtering and pagination
- **Catalog**: Sync from OpenMetadata, view and download catalog metadata

#### OpenMetadata Integration
- REST API client for OpenMetadata
- Automatic catalog synchronization
- Schema and lineage metadata extraction
- Catalog browsing and download endpoints
- Support for table-level metadata

#### Data Transfers
- S3/MinIO integration with boto3
- Presigned URL generation for secure transfers
- Support for both upload (PUT) and download (GET) operations
- Contract validation before transfers
- Configurable URL expiration times

#### Audit & Compliance
- Comprehensive audit logging for all operations
- Event types: publication_created, request_created, contract_signed, transfer_initiated, catalog_synced
- Paginated audit log queries
- User and resource tracking
- IDSA/DSSC compliance mapping

#### Testing
- Pytest test suite with fixtures
- Unit tests for models, API, and catalog
- Test coverage for main workflows
- SQLite in-memory database for tests
- GitHub Actions CI pipeline

#### Documentation
- Comprehensive README with setup instructions
- API usage examples with curl commands
- Complete workflow demonstration script
- Contributing guidelines
- Environment configuration examples
- Credential documentation

### Technical Details

**Stack:**
- FastAPI 0.104+
- SQLAlchemy 2.0+
- Alembic 1.12+
- Keycloak 23.0
- PostgreSQL 15
- MinIO (latest)
- OpenMetadata 1.3.0

**Security:**
- JWT token validation with JWKS
- Role-based authorization
- Secure credential management
- Presigned URLs with expiration
- Audit trail for all actions

**Compliance:**
- IDSA principles implementation
- DSSC recommendations
- Data sovereignty controls
- Contract-based access
- Full traceability

### Known Limitations

- OpenMetadata Python client not included due to dependency complexity (uses REST API directly)
- Default credentials are for development only
- SSL/TLS must be configured for production
- Rate limiting not implemented
- Email notifications not implemented

### Migration from Previous Version

This is the first production-ready release. Previous prototypes should migrate data manually.

---

## [0.1.0] - 2025-10-31 (Initial Prototype)

### Added
- Basic FastAPI application
- In-memory storage
- Simple OpenAPI documentation
- Docker Compose with basic services

### Removed in 1.0.0
- In-memory storage (replaced with PostgreSQL)
- Mock authentication (replaced with Keycloak)
- Simplified catalog (replaced with OpenMetadata integration)
