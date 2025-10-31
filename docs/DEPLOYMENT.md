# Deployment Guide

This guide covers deploying the Data Space in various environments.

## Table of Contents

1. [Development Deployment](#development-deployment)
2. [Production Deployment](#production-deployment)
3. [Cloud Deployments](#cloud-deployments)
4. [Security Hardening](#security-hardening)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Development Deployment

### Quick Start (Docker Compose)

```bash
# Clone repository
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Run quick start
./quickstart.sh

# Or manually
cp .env.local.example .env.local
docker-compose up -d
```

**Services:**
- API: http://localhost:8000
- Keycloak: http://localhost:8080
- MinIO: http://localhost:9001
- OpenMetadata: http://localhost:8585

### Local Development

```bash
# Install dependencies
pip install -e .[dev]

# Start infrastructure
docker-compose up -d db keycloak minio openmetadata

# Run migrations
alembic upgrade head

# Start API locally
uvicorn src.main:app --reload
```

## Production Deployment

### Prerequisites

- Docker and Docker Compose (or Kubernetes)
- SSL certificates
- Domain names
- Backup strategy
- Monitoring solution

### Environment Configuration

Create `.env.production`:

```bash
# Database
DATABASE_URL=postgresql://user:password@db-host:5432/dataspace

# Keycloak
KEYCLOAK_URL=https://auth.yourdomain.com
KEYCLOAK_REALM=dataspace
KEYCLOAK_CLIENT_ID=dataspace-api
KEYCLOAK_CLIENT_SECRET=<strong-secret>

# MinIO/S3
MINIO_ENDPOINT=s3.yourdomain.com:443
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
MINIO_SECURE=true
MINIO_BUCKET=dataspace-transfers

# OpenMetadata
OPENMETADATA_URL=https://metadata.yourdomain.com
OPENMETADATA_API_KEY=<api-key>
```

### Using Docker Compose (Production)

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    restart: always
    env_file: .env.production
    ports:
      - "8000:8000"
    depends_on:
      - db
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    restart: always
    env_file: .env.production
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./backups:/backups
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  # Add other services...

volumes:
  db-data:
    driver: local
```

Deploy:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Using Kubernetes

#### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dataspace
```

#### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dataspace-config
  namespace: dataspace
data:
  DATABASE_HOST: "postgres-service"
  KEYCLOAK_URL: "https://auth.yourdomain.com"
  # ... other non-secret configs
```

#### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: dataspace-secrets
  namespace: dataspace
type: Opaque
stringData:
  DATABASE_PASSWORD: "<password>"
  KEYCLOAK_CLIENT_SECRET: "<secret>"
  MINIO_SECRET_KEY: "<secret>"
```

#### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataspace-api
  namespace: dataspace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dataspace-api
  template:
    metadata:
      labels:
        app: dataspace-api
    spec:
      containers:
      - name: api
        image: dataspace-api:1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: dataspace-config
        - secretRef:
            name: dataspace-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

#### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: dataspace-api
  namespace: dataspace
spec:
  selector:
    app: dataspace-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:

```bash
kubectl apply -f k8s/
```

## Cloud Deployments

### AWS

**Components:**
- ECS/EKS for API
- RDS PostgreSQL for database
- S3 for object storage
- Cognito or managed Keycloak
- ALB for load balancing

**Setup:**

1. **Database (RDS)**
```bash
aws rds create-db-instance \
  --db-instance-identifier dataspace-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 100
```

2. **S3 Bucket**
```bash
aws s3 mb s3://dataspace-transfers
aws s3api put-bucket-versioning \
  --bucket dataspace-transfers \
  --versioning-configuration Status=Enabled
```

3. **ECS Deployment**
```bash
# Build and push image
docker build -t dataspace-api .
aws ecr create-repository --repository-name dataspace-api
docker tag dataspace-api:latest <account>.dkr.ecr.<region>.amazonaws.com/dataspace-api
docker push <account>.dkr.ecr.<region>.amazonaws.com/dataspace-api

# Create ECS cluster and service
aws ecs create-cluster --cluster-name dataspace
aws ecs create-service --cluster dataspace --service-name api --task-definition dataspace-api
```

### Azure

**Components:**
- AKS for API
- Azure Database for PostgreSQL
- Azure Blob Storage
- Azure AD B2C or managed Keycloak
- Application Gateway

**Setup:**

1. **Database**
```bash
az postgres server create \
  --resource-group dataspace-rg \
  --name dataspace-db \
  --location eastus \
  --admin-user admin \
  --admin-password <password> \
  --sku-name GP_Gen5_2
```

2. **Storage**
```bash
az storage account create \
  --name dataspacestorage \
  --resource-group dataspace-rg \
  --location eastus \
  --sku Standard_LRS
```

3. **AKS Deployment**
```bash
az aks create \
  --resource-group dataspace-rg \
  --name dataspace-aks \
  --node-count 3 \
  --generate-ssh-keys

kubectl apply -f k8s/
```

### GCP

**Components:**
- GKE for API
- Cloud SQL PostgreSQL
- Cloud Storage
- Identity Platform or managed Keycloak
- Cloud Load Balancing

## Security Hardening

### SSL/TLS Configuration

**Nginx Reverse Proxy:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Firewall Rules

```bash
# Allow only necessary ports
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (redirect to HTTPS)
ufw allow 443/tcp  # HTTPS
ufw enable
```

### Database Security

```sql
-- Create read-only user for reporting
CREATE USER dataspace_readonly WITH PASSWORD '<password>';
GRANT CONNECT ON DATABASE dataspace TO dataspace_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dataspace_readonly;

-- Enable audit logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_connections = 'on';
```

### Secrets Management

**Using Vault:**

```bash
# Store secrets
vault kv put secret/dataspace/db password=<db-password>
vault kv put secret/dataspace/keycloak client_secret=<secret>

# Retrieve in application
export DATABASE_PASSWORD=$(vault kv get -field=password secret/dataspace/db)
```

## Monitoring and Maintenance

### Health Checks

```bash
# API health
curl https://api.yourdomain.com/health

# Database connection
psql -h <db-host> -U dataspace_user -d dataspace -c "SELECT 1"

# Keycloak health
curl https://auth.yourdomain.com/health/ready
```

### Monitoring with Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'dataspace-api'
    static_configs:
      - targets: ['api:8000']
```

### Logging

**Centralized Logging with ELK:**

```yaml
# logstash.conf
input {
  file {
    path => "/var/log/dataspace/*.log"
    type => "dataspace"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "dataspace-%{+YYYY.MM.dd}"
  }
}
```

### Backup Strategy

**Database Backups:**

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -h localhost -U dataspace_user dataspace > $BACKUP_DIR/dataspace_$DATE.sql
gzip $BACKUP_DIR/dataspace_$DATE.sql

# Keep last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**S3/MinIO Backups:**

```bash
# Sync to backup location
aws s3 sync s3://dataspace-transfers s3://dataspace-backup/$(date +%Y%m%d)
```

### Maintenance Tasks

**Weekly:**
- Review audit logs
- Check database size
- Verify backups
- Update dependencies

**Monthly:**
- Review and rotate credentials
- Update SSL certificates if needed
- Performance tuning
- Capacity planning

### Troubleshooting

**Check logs:**
```bash
# Docker
docker-compose logs -f api

# Kubernetes
kubectl logs -f deployment/dataspace-api -n dataspace
```

**Database queries:**
```sql
-- Check active connections
SELECT * FROM pg_stat_activity WHERE datname = 'dataspace';

-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname = 'public';
```

## Performance Tuning

### API Optimization

```python
# Enable async operations
# Add caching
# Use connection pooling
```

### Database Optimization

```sql
-- Add indexes
CREATE INDEX idx_publications_fqn ON publications(openmetadata_fqn);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Analyze tables
ANALYZE publications;
```

### Load Testing

```bash
# Using locust
locust -f loadtest.py --host=https://api.yourdomain.com
```

## Disaster Recovery

**RTO (Recovery Time Objective):** 4 hours
**RPO (Recovery Point Objective):** 1 hour

**Recovery Steps:**

1. Restore database from latest backup
2. Restore MinIO data from backup
3. Redeploy application
4. Verify all services
5. Run smoke tests

---

For questions or issues during deployment, open an issue on GitHub.
