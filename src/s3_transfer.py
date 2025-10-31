import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional
from src.config import settings
import logging

logger = logging.getLogger(__name__)


class S3TransferService:
    """Service for handling S3/MinIO transfers with pre-signed URLs."""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version='s3v4'),
        )
        self.bucket = settings.s3_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if not."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            logger.info(f"Bucket '{self.bucket}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"Creating bucket '{self.bucket}'")
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Bucket '{self.bucket}' created successfully")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
            else:
                logger.error(f"Error checking bucket: {e}")

    def generate_presigned_upload_url(
        self,
        object_key: str,
        expiration: int = 3600,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Generate a pre-signed URL for uploading an object to S3.
        
        Args:
            object_key: The S3 key for the object
            expiration: URL expiration time in seconds (default: 1 hour)
            content_type: Optional content type for the upload
            
        Returns:
            Pre-signed URL for PUT operation
        """
        try:
            params = {
                'Bucket': self.bucket,
                'Key': object_key,
            }
            if content_type:
                params['ContentType'] = content_type

            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration,
            )
            logger.info(f"Generated upload URL for key: {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating upload URL: {e}")
            raise

    def generate_presigned_download_url(
        self,
        object_key: str,
        expiration: int = 3600,
    ) -> str:
        """
        Generate a pre-signed URL for downloading an object from S3.
        
        Args:
            object_key: The S3 key for the object
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Pre-signed URL for GET operation
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': object_key,
                },
                ExpiresIn=expiration,
            )
            logger.info(f"Generated download URL for key: {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating download URL: {e}")
            raise

    def upload_object(self, object_key: str, data: bytes, content_type: Optional[str] = None):
        """
        Directly upload an object to S3.
        
        Args:
            object_key: The S3 key for the object
            data: Binary data to upload
            content_type: Optional content type
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=data,
                **extra_args,
            )
            logger.info(f"Uploaded object to S3: {object_key}")
        except ClientError as e:
            logger.error(f"Error uploading object: {e}")
            raise

    def delete_object(self, object_key: str):
        """
        Delete an object from S3.
        
        Args:
            object_key: The S3 key for the object
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"Deleted object from S3: {object_key}")
        except ClientError as e:
            logger.error(f"Error deleting object: {e}")
            raise

    def object_exists(self, object_key: str) -> bool:
        """
        Check if an object exists in S3.
        
        Args:
            object_key: The S3 key for the object
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking object existence: {e}")
            raise


# Singleton instance
s3_service = S3TransferService()
