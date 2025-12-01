"""MinIO storage client with presigned URL support."""
import os
import uuid
import logging
from typing import Optional, BinaryIO
from datetime import timedelta

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

logger = logging.getLogger(__name__)

# Environment configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "dataspace")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")
PRESIGNED_URL_EXPIRY = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))  # 1 hour


class MinIOStorage:
    """MinIO storage client using boto3."""
    
    def __init__(
        self,
        endpoint: str = MINIO_ENDPOINT,
        access_key: str = MINIO_ACCESS_KEY,
        secret_key: str = MINIO_SECRET_KEY,
        bucket: str = MINIO_BUCKET,
        region: str = MINIO_REGION,
    ):
        self.endpoint = endpoint
        self.bucket = bucket
        self.region = region
        
        # Create S3 client configured for MinIO
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )
        
        self._ensure_bucket()
    
    def _ensure_bucket(self) -> None:
        """Ensure the bucket exists."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Created bucket: {self.bucket}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.warning(f"Could not check bucket: {e}")
    
    def generate_object_key(
        self,
        filename: str,
        provider_id: str,
        dataset_id: Optional[str] = None
    ) -> str:
        """Generate a unique object key for a file."""
        unique_id = str(uuid.uuid4())
        if dataset_id:
            return f"datasets/{provider_id}/{dataset_id}/{unique_id}_{filename}"
        return f"uploads/{provider_id}/{unique_id}_{filename}"
    
    def get_presigned_put_url(
        self,
        object_key: str,
        content_type: str = "application/octet-stream",
        expiry: int = PRESIGNED_URL_EXPIRY
    ) -> str:
        """Generate a presigned URL for uploading."""
        try:
            url = self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expiry,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned PUT URL: {e}")
            raise
    
    def get_presigned_get_url(
        self,
        object_key: str,
        expiry: int = PRESIGNED_URL_EXPIRY
    ) -> str:
        """Generate a presigned URL for downloading."""
        try:
            url = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": object_key,
                },
                ExpiresIn=expiry,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned GET URL: {e}")
            raise
    
    async def upload_file(
        self,
        file: UploadFile,
        object_key: str
    ) -> dict:
        """Upload a file directly to MinIO (server-side upload)."""
        try:
            content = await file.read()
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=content,
                ContentType=file.content_type or "application/octet-stream",
            )
            
            return {
                "object_key": object_key,
                "bucket": self.bucket,
                "size": len(content),
                "content_type": file.content_type,
            }
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    def upload_bytes(
        self,
        data: bytes,
        object_key: str,
        content_type: str = "application/octet-stream"
    ) -> dict:
        """Upload bytes directly to MinIO."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )
            
            return {
                "object_key": object_key,
                "bucket": self.bucket,
                "size": len(data),
                "content_type": content_type,
            }
        except ClientError as e:
            logger.error(f"Failed to upload bytes: {e}")
            raise
    
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None
    ) -> dict:
        """Copy an object within MinIO."""
        source_bucket = source_bucket or self.bucket
        try:
            self.client.copy_object(
                Bucket=self.bucket,
                Key=dest_key,
                CopySource={"Bucket": source_bucket, "Key": source_key},
            )
            return {
                "source_key": source_key,
                "dest_key": dest_key,
                "bucket": self.bucket,
            }
        except ClientError as e:
            logger.error(f"Failed to copy object: {e}")
            raise
    
    def delete_object(self, object_key: str) -> bool:
        """Delete an object from MinIO."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete object: {e}")
            return False
    
    def object_exists(self, object_key: str) -> bool:
        """Check if an object exists."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError:
            return False
    
    def get_object_info(self, object_key: str) -> Optional[dict]:
        """Get object metadata."""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=object_key)
            return {
                "object_key": object_key,
                "bucket": self.bucket,
                "size": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError:
            return None


# Global storage instance
_storage: Optional[MinIOStorage] = None


def get_storage() -> MinIOStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = MinIOStorage()
    return _storage
