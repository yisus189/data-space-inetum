import logging
from typing import Optional
from datetime import datetime, timedelta
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from src.config import settings

logger = logging.getLogger(__name__)


class S3TransferService:
    """Service for managing S3/MinIO transfers"""
    
    def __init__(self):
        self.endpoint = f"{'https' if settings.minio_secure else 'http'}://{settings.minio_endpoint}"
        self.bucket_name = settings.minio_bucket
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        # Ensure bucket exists
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
            else:
                logger.error(f"Error checking bucket: {e}")
    
    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        method: str = 'get_object'
    ) -> Optional[str]:
        """
        Generate a presigned URL for S3 object access.
        
        Args:
            object_key: Key/path of the object in S3
            expiration: URL expiration time in seconds (default: 1 hour)
            method: S3 method to presign ('get_object' or 'put_object')
        
        Returns:
            Presigned URL string or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {object_key}, expires in {expiration}s")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    def generate_download_url(
        self,
        object_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a presigned download URL.
        
        Args:
            object_key: Key/path of the object to download
            expiration: URL expiration time in seconds
        
        Returns:
            Presigned download URL
        """
        return self.generate_presigned_url(object_key, expiration, 'get_object')
    
    def generate_upload_url(
        self,
        object_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a presigned upload URL.
        
        Args:
            object_key: Key/path where the object will be uploaded
            expiration: URL expiration time in seconds
        
        Returns:
            Presigned upload URL
        """
        return self.generate_presigned_url(object_key, expiration, 'put_object')
    
    def upload_object(
        self,
        object_key: str,
        data: bytes,
        content_type: Optional[str] = None
    ) -> bool:
        """
        Upload an object to S3.
        
        Args:
            object_key: Key/path for the object
            data: Binary data to upload
            content_type: Content type (e.g., 'application/json')
        
        Returns:
            True if successful, False otherwise
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=data,
                **extra_args
            )
            logger.info(f"Uploaded object: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload object: {e}")
            return False
    
    def download_object(self, object_key: str) -> Optional[bytes]:
        """
        Download an object from S3.
        
        Args:
            object_key: Key/path of the object to download
        
        Returns:
            Object data as bytes or None if failed
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            data = response['Body'].read()
            logger.info(f"Downloaded object: {object_key}")
            return data
        except ClientError as e:
            logger.error(f"Failed to download object: {e}")
            return None
    
    def object_exists(self, object_key: str) -> bool:
        """
        Check if an object exists in S3.
        
        Args:
            object_key: Key/path of the object
        
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError:
            return False
    
    def get_expiration_timestamp(self, expiration_seconds: int = 3600) -> str:
        """
        Get expiration timestamp string.
        
        Args:
            expiration_seconds: Expiration time in seconds from now
        
        Returns:
            ISO format timestamp string
        """
        expiration_time = datetime.utcnow() + timedelta(seconds=expiration_seconds)
        return expiration_time.isoformat() + 'Z'


# Global instance
s3_service = S3TransferService()


def get_s3_service() -> S3TransferService:
    """Get S3 transfer service instance"""
    return s3_service
