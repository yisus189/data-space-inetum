# Complete Setup Guide

This guide walks you through setting up the complete Data Space environment from scratch.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 8GB+ RAM available
- Ports 3000, 8000, 8080, 8585, 9000-9001, 5432, 6379 free

## Step 1: Clone and Configure

```bash
# Clone repository
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Copy environment configuration
cp .env.example .env

# Optional: Edit .env for custom configuration
nano .env
```

## Step 2: Start Infrastructure Services

Start the infrastructure services first (database, Keycloak, MinIO, etc.):

```bash
# Start all services
docker-compose up -d

# Monitor logs
docker-compose logs -f
```

**Wait for all services to be healthy** (usually 2-3 minutes). You can check status:

```bash
docker-compose ps
```

All services should show "healthy" status.

## Step 3: Initialize Database

Once PostgreSQL is ready, initialize the database schema:

```bash
# Create database tables
docker-compose exec api python scripts/init_db.py
```

You should see output confirming tables were created.

## Step 4: Verify Services

### Backend API

```bash
# Health check
curl http://localhost:8000/metrics/health

# Expected response: {"status":"healthy","timestamp":...}

# List datasets (should be empty initially)
curl http://localhost:8000/datasets

# Expected response: []
```

### Keycloak

1. Open http://localhost:8080
2. Click "Administration Console"
3. Login with: `admin` / `admin`
4. Verify realm `myrealm` exists
5. Check that test users exist:
   - `provider1` / `provider123` (Provider role)
   - `consumer1` / `consumer123` (Consumer role)

### MinIO

1. Open http://localhost:9001
2. Login with: `minioadmin` / `minioadmin`
3. Verify bucket `dataspace` exists (created automatically)

### Frontend

1. Open http://localhost:3000
2. Should see "Data Space Inetum" homepage
3. Public catalog should be visible (empty initially)

## Step 5: Test Authentication Flow

### Get Access Token

```bash
# Login as provider
curl -X POST http://localhost:8080/realms/myrealm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=dataspace-ui" \
  -d "username=provider1" \
  -d "password=provider123" | jq -r '.access_token'

# Save token to variable
export TOKEN="<your_access_token_here>"
```

### Test Authenticated Endpoint

```bash
# Upload a test dataset
echo "test,data,csv" > test.csv

curl -X POST http://localhost:8000/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Test Dataset" \
  -F "description=My first dataset" \
  -F "file=@test.csv"

# Expected response with dataset ID
```

## Step 6: Test Frontend Login

1. Go to http://localhost:3000
2. Click "Login" in top right
3. Login with `provider1` / `provider123`
4. Should redirect back to homepage
5. You should now see "My Datasets" and "Upload" buttons

## Step 7: Upload Dataset via Frontend

1. Click "Upload" button
2. Fill in:
   - Title: "My First Dataset"
   - Description: "Test upload from frontend"
   - Choose a file (CSV, JSON, or any file)
3. Click "Upload"
4. Should redirect to "My Datasets" showing your uploaded dataset

## Step 8: Publish Dataset

1. In "My Datasets", find your dataset
2. Click "Publish" button
3. Dataset status should change from "draft" to "public"
4. Logout and verify dataset is now visible in public catalog

## Step 9: Test OpenMetadata Integration (Optional)

If you have OpenMetadata configured:

1. Login as provider
2. Go to "Provider Dashboard"
3. Click "OpenMetadata Catalog" tab
4. Browse available entities
5. Click "Import" on an entity
6. Choose whether to copy data or just link
7. Dataset will be created with OpenMetadata reference

## Step 10: Test Download Flow

1. Open a published dataset detail page
2. Login as consumer (`consumer1` / `consumer123`)
3. Click "Download" button
4. Should get a presigned URL and file downloads

## Troubleshooting

### Services Not Starting

```bash
# Check logs for errors
docker-compose logs api
docker-compose logs keycloak
docker-compose logs db

# Restart a specific service
docker-compose restart api
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps db

# Test connection
docker-compose exec db psql -U dataspace_user -d dataspace -c "\dt"
```

### Keycloak Issues

```bash
# Check Keycloak logs
docker-compose logs keycloak

# Restart Keycloak
docker-compose restart keycloak

# Wait for it to be healthy
docker-compose ps keycloak
```

### MinIO Connection Errors

```bash
# Check MinIO is running
docker-compose ps minio

# Access MinIO console
open http://localhost:9001

# Verify bucket exists in console
```

### Frontend Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

### Token Verification Errors

Common issues:
1. **Wrong audience**: Ensure `KEYCLOAK_CLIENT_ID` matches in both backend and frontend
2. **Clock skew**: Ensure Docker container times are synchronized
3. **Expired token**: Tokens expire after 1 hour by default, get a new one

### Port Conflicts

If ports are already in use:

```bash
# Check what's using a port
lsof -i :8000
lsof -i :3000

# Stop conflicting service or change port in docker-compose.yml
```

## Running Tests

### Unit Tests

```bash
# Run all tests
docker-compose exec api pytest tests/ -v

# Run specific test file
docker-compose exec api pytest tests/test_jwks.py -v

# Run with coverage
docker-compose exec api pytest tests/ --cov=src --cov-report=html
```

### E2E Smoke Tests

```bash
# Ensure services are running
docker-compose up -d

# Run smoke tests
python tests/smoke_test.py
```

### CI/CD

The GitHub Actions workflow runs automatically on:
- Push to `main` or `copilot/**` branches
- Pull requests to `main`

Check `.github/workflows/ci.yml` for details.

## Next Steps

1. **Configure Production Settings**:
   - Change all default passwords
   - Set up SSL/TLS
   - Configure proper database backups
   - Review security checklist in README

2. **Integrate Real OpenMetadata**:
   - Configure OpenMetadata URL and API key
   - Set up data sources in OpenMetadata
   - Test catalog import

3. **Set Up EDC** (Optional):
   - Deploy Eclipse Dataspace Connector
   - Configure EDC Management API
   - Map datasets to EDC assets
   - See `src/app/routers/edc.py` for integration guide

4. **Customize Frontend**:
   - Update branding and theme
   - Add custom pages
   - Implement additional features

5. **Add Monitoring**:
   - Set up Prometheus scraping
   - Configure Grafana dashboards
   - Set up alerting

## Support

- Issues: https://github.com/yisus189/data-space-inetum/issues
- Documentation: See `/docs` directory
- IDSA Specification: https://github.com/International-Data-Spaces-Association/IDS-G
