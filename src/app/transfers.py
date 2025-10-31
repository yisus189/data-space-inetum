"""S3/MinIO transfer utilities."""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "dataspace-transfers")

# Create S3 client
s3_client = boto3.client(
    's3',
    endpoint_url=f"{'https' if MINIO_SECURE else 'http'}://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)


def ensure_bucket_exists():
    """Ensure the MinIO bucket exists."""
    try:
        s3_client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        # Bucket doesn't exist, create it
        try:
            s3_client.create_bucket(Bucket=MINIO_BUCKET)
        except Exception as e:
            print(f"Error creating bucket: {e}")


def generate_presigned_url(
    object_key: str,
    operation: str = "put_object",
    expires_in: int = 3600
) -> str:
    """Generate a presigned URL for S3 operations.
    
    Args:
        object_key: S3 object key
        operation: S3 operation (put_object or get_object)
        expires_in: URL expiration time in seconds
    
    Returns:
        Presigned URL string
    """
    try:
        url = s3_client.generate_presigned_url(
            operation,
            Params={
                'Bucket': MINIO_BUCKET,
                'Key': object_key
            },
            ExpiresIn=expires_in
        )
        return url
    except Exception as e:
        raise Exception(f"Failed to generate presigned URL: {str(e)}")
