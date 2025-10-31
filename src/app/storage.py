"""
S3/MinIO integration for data transfers
"""
import os
import logging
from datetime import timedelta
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# MinIO/S3 Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "dataspace-transfers")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"


class S3Client:
    """S3/MinIO client for data transfers"""
    
    def __init__(self):
        endpoint_url = f"{'https' if MINIO_USE_SSL else 'http'}://{MINIO_ENDPOINT}"
        
        logger.info(f"Initializing S3 client for endpoint: {endpoint_url}")
        
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        self.bucket = MINIO_BUCKET
    
    def ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"Bucket '{self.bucket}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"Creating bucket '{self.bucket}'")
                self.client.create_bucket(Bucket=self.bucket)
                logger.info(f"Bucket '{self.bucket}' created successfully")
            else:
                logger.error(f"Error checking bucket: {e}")
                raise
    
    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        operation: str = 'get_object'
    ) -> str:
        """
        Generate a presigned URL for downloading or uploading data
        
        Args:
            object_key: The S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            operation: 'get_object' for download, 'put_object' for upload
        
        Returns:
            Presigned URL as string
        """
        logger.info(
            f"Generating presigned URL for {operation} operation on '{object_key}' "
            f"(expires in {expiration}s)"
        )
        
        try:
            url = self.client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket, 'Key': object_key},
                ExpiresIn=expiration
            )
            logger.info(f"Presigned URL generated successfully")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def upload_file(self, file_path: str, object_key: str):
        """Upload a file to S3/MinIO"""
        logger.info(f"Uploading file '{file_path}' to '{object_key}'")
        
        try:
            self.client.upload_file(file_path, self.bucket, object_key)
            logger.info(f"File uploaded successfully")
        except ClientError as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def create_transfer_object(self, transfer_id: str, metadata: dict = None) -> str:
        """
        Create a placeholder object for a transfer and return presigned URL
        
        Args:
            transfer_id: Unique transfer identifier
            metadata: Optional metadata to attach to the object
        
        Returns:
            Presigned download URL
        """
        object_key = f"transfers/{transfer_id}/data"
        
        logger.info(f"Creating transfer object for transfer_id={transfer_id}")
        
        # Create a minimal placeholder object
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
            
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=b'',
                **extra_args
            )
            
            logger.info(f"Transfer object created at '{object_key}'")
            
            # Generate presigned URL for download
            url = self.generate_presigned_url(object_key, expiration=86400)  # 24 hours
            return url
            
        except ClientError as e:
            logger.error(f"Error creating transfer object: {e}")
            raise


def get_s3_client() -> S3Client:
    """Get S3/MinIO client instance"""
    client = S3Client()
    client.ensure_bucket_exists()
    return client
