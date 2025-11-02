"""Transfer module."""

from .s3 import (
    get_s3_client,
    ensure_bucket_exists,
    generate_presigned_upload_url,
    generate_presigned_download_url,
    upload_file,
    get_object_metadata,
    S3TransferError
)

__all__ = [
    "get_s3_client",
    "ensure_bucket_exists",
    "generate_presigned_upload_url",
    "generate_presigned_download_url",
    "upload_file",
    "get_object_metadata",
    "S3TransferError"
]
