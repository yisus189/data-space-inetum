"""S3/MinIO transfer utilities for presigned URLs."""

import os
import logging
from datetime import timedelta
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from botocore.client import Config

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "dataspace-transfers")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"


class S3TransferError(Exception):
    """S3 transfer error."""
    pass


def get_s3_client():
    """Get configured S3 client for MinIO."""
    try:
        # Configure endpoint URL
        endpoint_url = f"{'https' if MINIO_USE_SSL else 'http'}://{MINIO_ENDPOINT}"
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'  # MinIO doesn't care about region
        )
        
        return s3_client
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise S3TransferError(f"S3 client creation failed: {e}")


def ensure_bucket_exists(bucket_name: str = None) -> bool:
    """Ensure the S3 bucket exists, create if not."""
    if not bucket_name:
        bucket_name = MINIO_BUCKET
    
    try:
        s3_client = get_s3_client()
        
        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket {bucket_name} exists")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                logger.info(f"Creating bucket {bucket_name}")
                s3_client.create_bucket(Bucket=bucket_name)
                return True
            else:
                raise
    except Exception as e:
        logger.error(f"Error ensuring bucket exists: {e}")
        return False


def generate_presigned_upload_url(
    object_key: str,
    bucket_name: str = None,
    expiration: int = 3600
) -> Optional[str]:
    """
    Generate presigned URL for uploading an object.
    
    Args:
        object_key: S3 object key (path)
        bucket_name: Bucket name (defaults to MINIO_BUCKET)
        expiration: URL expiration in seconds (default 1 hour)
    
    Returns:
        Presigned URL string or None on error
    """
    if not bucket_name:
        bucket_name = MINIO_BUCKET
    
    try:
        s3_client = get_s3_client()
        
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
            },
            ExpiresIn=expiration
        )
        
        logger.info(f"Generated presigned upload URL for {object_key}")
        return url
        
    except ClientError as e:
        logger.error(f"Error generating presigned upload URL: {e}")
        raise S3TransferError(f"Failed to generate upload URL: {e}")


def generate_presigned_download_url(
    object_key: str,
    bucket_name: str = None,
    expiration: int = 3600
) -> Optional[str]:
    """
    Generate presigned URL for downloading an object.
    
    Args:
        object_key: S3 object key (path)
        bucket_name: Bucket name (defaults to MINIO_BUCKET)
        expiration: URL expiration in seconds (default 1 hour)
    
    Returns:
        Presigned URL string or None on error
    """
    if not bucket_name:
        bucket_name = MINIO_BUCKET
    
    try:
        s3_client = get_s3_client()
        
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
            },
            ExpiresIn=expiration
        )
        
        logger.info(f"Generated presigned download URL for {object_key}")
        return url
        
    except ClientError as e:
        logger.error(f"Error generating presigned download URL: {e}")
        raise S3TransferError(f"Failed to generate download URL: {e}")


def upload_file(file_path: str, object_key: str, bucket_name: str = None) -> bool:
    """
    Upload a file to S3.
    
    Args:
        file_path: Local file path
        object_key: S3 object key (destination path)
        bucket_name: Bucket name (defaults to MINIO_BUCKET)
    
    Returns:
        True if successful, False otherwise
    """
    if not bucket_name:
        bucket_name = MINIO_BUCKET
    
    try:
        s3_client = get_s3_client()
        
        s3_client.upload_file(file_path, bucket_name, object_key)
        logger.info(f"Uploaded {file_path} to s3://{bucket_name}/{object_key}")
        return True
        
    except ClientError as e:
        logger.error(f"Error uploading file: {e}")
        return False


def get_object_metadata(object_key: str, bucket_name: str = None) -> Optional[dict]:
    """
    Get metadata for an S3 object.
    
    Args:
        object_key: S3 object key
        bucket_name: Bucket name (defaults to MINIO_BUCKET)
    
    Returns:
        Metadata dict or None if object doesn't exist
    """
    if not bucket_name:
        bucket_name = MINIO_BUCKET
    
    try:
        s3_client = get_s3_client()
        
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        return {
            'size': response.get('ContentLength'),
            'last_modified': response.get('LastModified'),
            'content_type': response.get('ContentType'),
            'metadata': response.get('Metadata', {})
        }
        
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.warning(f"Object not found: s3://{bucket_name}/{object_key}")
            return None
        logger.error(f"Error getting object metadata: {e}")
        return None
