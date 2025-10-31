# S3/MinIO Configuration Guide

This guide explains how to configure S3 or MinIO for data transfers.

## MinIO for Local Development

MinIO is included in the docker-compose configuration for local development.

### Access MinIO Console

1. Navigate to http://localhost:9001
2. Login with:
   - Username: `minioadmin`
   - Password: `minioadmin`

### Default Configuration

The MinIO service is configured with:
- **Endpoint**: `http://localhost:9000` (API)
- **Console**: `http://localhost:9001` (UI)
- **Access Key**: `minioadmin`
- **Secret Key**: `minioadmin`
- **Bucket**: `dataspace-transfers` (auto-created by the application)

### Testing MinIO

#### Using MinIO Client (mc)

Install MinIO client:
```bash
brew install minio/stable/mc  # macOS
# or
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
```

Configure alias:
```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
```

List buckets:
```bash
mc ls local
```

Upload a file:
```bash
mc cp myfile.txt local/dataspace-transfers/
```

#### Using AWS CLI

Install AWS CLI and configure:
```bash
aws configure set aws_access_key_id minioadmin
aws configure set aws_secret_access_key minioadmin
```

List buckets:
```bash
aws --endpoint-url http://localhost:9000 s3 ls
```

Upload a file:
```bash
aws --endpoint-url http://localhost:9000 s3 cp myfile.txt s3://dataspace-transfers/
```

## AWS S3 for Production

### Prerequisites

1. AWS account
2. IAM user with S3 permissions
3. S3 bucket created

### Configuration

Update your `.env` file:

```bash
S3_ENDPOINT_URL=  # Leave empty for AWS S3
S3_ACCESS_KEY=AKIA...  # Your AWS access key
S3_SECRET_KEY=wJalrX...  # Your AWS secret key
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1  # Your bucket region
```

### IAM Policy

Create an IAM user with this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

### Bucket Configuration

#### CORS Configuration (if accessing from browser)

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": ["ETag"]
  }
]
```

#### Lifecycle Policy (optional)

To automatically delete old transfer files:

```json
{
  "Rules": [
    {
      "Id": "DeleteOldTransfers",
      "Status": "Enabled",
      "Prefix": "transfers/",
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

## Pre-signed URLs

### How It Works

1. **Consumer requests a transfer** via API
2. **API validates the contract** is active
3. **API generates S3 key**: `transfers/{contract_id}/{destination}`
4. **API creates pre-signed URL** with expiration (1 hour)
5. **Consumer receives URL** in the transfer response
6. **Consumer uploads data** directly to S3 using the URL
7. **Consumer marks transfer as complete** via API

### Security Features

- **Time-limited**: URLs expire after 1 hour by default
- **Contract-based**: Only valid contracts can create transfers
- **Audit trail**: All transfers are logged
- **Direct upload**: Data never goes through the API server

### Example Flow

#### 1. Create Transfer

Request:
```bash
curl -X POST "http://localhost:8000/transfers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "contract-123",
    "destination": "customer-data.csv"
  }'
```

Response:
```json
{
  "id": "transfer-456",
  "contract_id": "contract-123",
  "destination": "customer-data.csv",
  "state": "in_progress",
  "presigned_url": "http://localhost:9000/dataspace-transfers/transfers/contract-123/customer-data.csv?X-Amz-Algorithm=...",
  "s3_key": "transfers/contract-123/customer-data.csv",
  "created_at": "2025-10-31T14:00:00Z"
}
```

#### 2. Upload Data

```bash
curl -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: text/csv" \
  --data-binary "@customer-data.csv"
```

#### 3. Mark as Complete

```bash
curl -X POST "http://localhost:8000/transfers/transfer-456/complete" \
  -H "Authorization: Bearer $TOKEN"
```

## Advanced Configuration

### Custom Expiration Time

Modify `src/s3_transfer.py`:

```python
def generate_presigned_upload_url(
    self,
    object_key: str,
    expiration: int = 7200,  # 2 hours instead of 1
    content_type: Optional[str] = None,
) -> str:
    # ...
```

### Content Type Validation

To enforce content types:

```python
presigned_url = s3_service.generate_presigned_upload_url(
    s3_key, 
    expiration=3600,
    content_type="text/csv"  # Only accept CSV files
)
```

### Server-Side Encryption

Enable encryption in boto3 client:

```python
self.s3_client.put_object(
    Bucket=self.bucket,
    Key=object_key,
    Body=data,
    ServerSideEncryption='AES256'  # or 'aws:kms'
)
```

## Monitoring & Logging

### Enable S3 Access Logging

For AWS S3:
1. Create logging bucket
2. Enable access logging on your data bucket
3. Logs will be written to logging bucket

For MinIO:
```bash
mc admin config set local logger_webhook:1 endpoint=http://your-webhook-url
mc admin service restart local
```

### CloudWatch Metrics (AWS)

Enable S3 metrics in AWS Console:
1. Go to S3 bucket
2. Navigate to "Metrics" tab
3. Enable "Request metrics"

### Monitor Transfer Success Rate

Query audit logs:
```sql
SELECT 
  event_type,
  COUNT(*) as count
FROM audit_logs
WHERE event_type LIKE 'transfer_%'
GROUP BY event_type;
```

## Troubleshooting

### Pre-signed URL Expired

**Error**: "Request has expired"

**Solution**: URLs expire after 1 hour by default. Create a new transfer or increase expiration time.

### Access Denied

**Error**: "Access Denied"

**Possible causes**:
1. Incorrect credentials
2. IAM policy doesn't allow operation
3. Bucket doesn't exist
4. Wrong region

**Solution**: Verify credentials and bucket configuration.

### CORS Error (Browser Upload)

**Error**: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solution**: Configure CORS policy on the bucket (see above).

### Connection Refused

**Error**: "Connection refused to MinIO"

**Solution**: 
- Check if MinIO container is running: `docker ps`
- Verify endpoint URL in .env
- Check network connectivity

## Alternative Storage Backends

### Azure Blob Storage

Install azure-storage-blob:
```bash
pip install azure-storage-blob
```

Implement Azure connector:
```python
from azure.storage.blob import BlobServiceClient, generate_blob_sas

class AzureBlobService:
    def generate_presigned_upload_url(self, blob_name: str):
        # Generate SAS token for upload
        pass
```

### Google Cloud Storage

Install google-cloud-storage:
```bash
pip install google-cloud-storage
```

Implement GCS connector:
```python
from google.cloud import storage

class GCSService:
    def generate_presigned_upload_url(self, object_name: str):
        # Generate signed URL
        pass
```

## Best Practices

1. **Use separate buckets** for different environments (dev/staging/prod)
2. **Enable versioning** for important data
3. **Configure lifecycle policies** to manage costs
4. **Monitor access patterns** for security
5. **Use encryption** at rest and in transit
6. **Implement access logging** for compliance
7. **Regular backup** of critical data
8. **Set bucket policies** to restrict public access

## References

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
