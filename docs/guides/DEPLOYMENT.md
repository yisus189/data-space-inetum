# Deployment Guide

This guide covers deploying the Data Space application in different environments.

## Local Development

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yisus189/data-space-inetum.git
   cd data-space-inetum
   ```

2. **Start all services**:
   ```bash
   docker-compose up --build
   ```

3. **Wait for all services to be ready** (approximately 1-2 minutes)

4. **Verify services**:
   - API Health: `curl http://localhost:8000/health`
   - Keycloak: http://localhost:8080
   - MinIO: http://localhost:9001

### Development with Hot Reload

The API service is configured with volume mounts for hot reload:

```bash
# Edit code in src/
# Changes are automatically reloaded
```

To see logs:
```bash
docker-compose logs -f api
```

## Production Deployment

### Prerequisites

- Docker and Docker Compose (or Kubernetes)
- PostgreSQL database (external, managed service recommended)
- S3-compatible object storage (AWS S3, MinIO, etc.)
- Keycloak instance (external, HA setup recommended)
- Domain name and SSL certificates

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      OPENMETADATA_URL: ${OPENMETADATA_URL}
      OPENMETADATA_API_KEY: ${OPENMETADATA_API_KEY}
      KEYCLOAK_SERVER_URL: ${KEYCLOAK_SERVER_URL}
      KEYCLOAK_REALM: ${KEYCLOAK_REALM}
      KEYCLOAK_CLIENT_ID: ${KEYCLOAK_CLIENT_ID}
      KEYCLOAK_CLIENT_SECRET: ${KEYCLOAK_CLIENT_SECRET}
      S3_ENDPOINT_URL: ${S3_ENDPOINT_URL:-}
      S3_ACCESS_KEY: ${S3_ACCESS_KEY}
      S3_SECRET_KEY: ${S3_SECRET_KEY}
      S3_BUCKET: ${S3_BUCKET}
      S3_REGION: ${S3_REGION}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Environment Variables for Production

Create `.env.prod`:

```bash
# Database (use managed PostgreSQL)
DATABASE_URL=postgresql+psycopg://user:password@db.example.com:5432/dataspace

# Keycloak (use external instance)
KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_REALM=dataspace
KEYCLOAK_CLIENT_ID=dataspace-api
KEYCLOAK_CLIENT_SECRET=your-secure-secret

# AWS S3
S3_ENDPOINT_URL=  # Leave empty for AWS S3
S3_ACCESS_KEY=AKIA...
S3_SECRET_KEY=...
S3_BUCKET=production-dataspace-transfers
S3_REGION=us-east-1

# OpenMetadata (optional)
OPENMETADATA_URL=https://openmetadata.example.com
OPENMETADATA_API_KEY=your-api-key

# Audit
AUDIT_WEBHOOK_URL=https://webhook.example.com/audit
```

### Reverse Proxy (nginx)

Create `nginx.conf`:

```nginx
upstream dataspace_api {
    server api:8000;
}

server {
    listen 80;
    server_name dataspace.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dataspace.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://dataspace_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        proxy_pass http://dataspace_api/health;
        access_log off;
    }
}
```

Add nginx to docker-compose:

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, etc.)
- kubectl configured
- Helm (optional, recommended)

### ConfigMap for Configuration

`k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dataspace-config
data:
  KEYCLOAK_SERVER_URL: "https://keycloak.example.com"
  KEYCLOAK_REALM: "dataspace"
  KEYCLOAK_CLIENT_ID: "dataspace-api"
  S3_BUCKET: "production-dataspace-transfers"
  S3_REGION: "us-east-1"
```

### Secret for Sensitive Data

```bash
kubectl create secret generic dataspace-secrets \
  --from-literal=DATABASE_URL='postgresql+psycopg://user:pass@host:5432/db' \
  --from-literal=KEYCLOAK_CLIENT_SECRET='secret' \
  --from-literal=S3_ACCESS_KEY='key' \
  --from-literal=S3_SECRET_KEY='secret' \
  --from-literal=OPENMETADATA_API_KEY='key'
```

### Deployment

`k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataspace-api
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
        image: your-registry/dataspace-api:latest
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
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Service

`k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: dataspace-api
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: dataspace-api
```

### Ingress

`k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dataspace-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - dataspace.example.com
    secretName: dataspace-tls
  rules:
  - host: dataspace.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dataspace-api
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Check deployment
kubectl get pods
kubectl get services
kubectl get ingress

# View logs
kubectl logs -f deployment/dataspace-api
```

## Database Migration in Production

### Before Deployment

Run migrations before deploying new code:

```bash
# SSH into server or use CI/CD
alembic upgrade head
```

### Automated Migration in CI/CD

Add to your CI/CD pipeline:

```yaml
- name: Run Database Migrations
  run: |
    pip install alembic psycopg
    export DATABASE_URL=${{ secrets.DATABASE_URL }}
    alembic upgrade head
```

### Rollback Procedure

If migration fails:

```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>
```

## Monitoring & Observability

### Health Checks

The application exposes a health endpoint:

```bash
curl https://dataspace.example.com/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Data Space API"
}
```

### Prometheus Metrics (Optional Enhancement)

Add prometheus-fastapi-instrumentator:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)
Instrumentator().instrument(app).expose(app)
```

### Logging

Application logs are output to stdout/stderr. Configure log aggregation:

- **Docker**: Use log drivers (json-file, syslog, etc.)
- **Kubernetes**: Use Fluentd/Fluent Bit to collect logs
- **Cloud**: Use CloudWatch, Stackdriver, etc.

### Monitoring Checklist

- [ ] CPU and memory usage
- [ ] Request rate and latency
- [ ] Error rate (4xx, 5xx)
- [ ] Database connection pool
- [ ] S3 transfer success rate
- [ ] Audit log growth rate

## Backup & Recovery

### Database Backups

**Automated backups** (PostgreSQL):

```bash
# Daily backup
pg_dump -U dataspace_user -h db.example.com dataspace > backup_$(date +%Y%m%d).sql

# Restore
psql -U dataspace_user -h db.example.com dataspace < backup_20251031.sql
```

### S3 Data Retention

Configure lifecycle policies:
- Keep transfers for 30 days
- Archive to Glacier after 90 days
- Delete after 1 year

## Security Best Practices

### Checklist

- [ ] Use HTTPS/TLS everywhere
- [ ] Store secrets in secret manager (AWS Secrets Manager, Vault)
- [ ] Enable database encryption at rest
- [ ] Enable S3 bucket encryption
- [ ] Use IAM roles instead of access keys (when possible)
- [ ] Implement rate limiting
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Network segmentation
- [ ] Firewall rules (allow only necessary ports)

### Secrets Management

Use external secret management:

```python
# Example with AWS Secrets Manager
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In config.py
secrets = get_secret('dataspace/prod')
settings.database_url = secrets['DATABASE_URL']
```

## Scaling Considerations

### Horizontal Scaling

- Run multiple API instances behind load balancer
- Database connection pooling per instance
- Stateless API design (no in-memory state)

### Vertical Scaling

- Increase memory for larger datasets
- More CPU for faster processing

### Database Scaling

- Read replicas for read-heavy workloads
- Connection pooling (PgBouncer)
- Query optimization and indexing

### S3 Optimization

- Use S3 Transfer Acceleration for large files
- Enable multipart upload for files > 100MB
- Use CloudFront CDN for frequently accessed files

## Troubleshooting Production Issues

### API Not Starting

1. Check logs: `docker logs <container>` or `kubectl logs <pod>`
2. Verify environment variables
3. Check database connectivity
4. Verify Keycloak is accessible

### Database Connection Errors

1. Check DATABASE_URL format
2. Verify network connectivity
3. Check database credentials
4. Ensure database is running
5. Check connection pool settings

### Authentication Failures

1. Verify Keycloak URL is accessible
2. Check client ID and secret
3. Verify realm name
4. Check JWT token expiration

### Transfer Failures

1. Verify S3 credentials
2. Check bucket exists
3. Verify network connectivity to S3
4. Check pre-signed URL expiration
5. Review transfer state in database

## Cost Optimization

### AWS

- Use Reserved Instances for predictable workloads
- S3 Intelligent-Tiering for varying access patterns
- RDS Reserved Instances for database
- CloudWatch Logs retention policies

### Resource Limits

Set appropriate limits in Kubernetes:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Compliance & Auditing

### GDPR Compliance

- Audit logs track all data access
- User consent recorded in contracts
- Right to erasure (implement data deletion)
- Data transfer logs for cross-border transfers

### Audit Log Retention

Configure retention policy:
```sql
-- Delete audit logs older than 1 year
DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '1 year';
```

Or archive to cold storage (S3 Glacier).

## References

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Production Best Practices](https://www.postgresql.org/docs/current/runtime-config.html)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
