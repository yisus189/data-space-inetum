"""Tests for storage client."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from src.storage.client import StorageClient, get_storage_client


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 S3 client."""
    with patch('src.storage.client.boto3.client') as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        yield mock_s3


class TestStorageClient:
    """Test MinIO/S3 storage client."""
    
    def test_initialization(self, mock_boto3_client):
        """Test storage client initialization."""
        mock_boto3_client.head_bucket.return_value = {}
        
        client = StorageClient()
        
        assert client.bucket == "dataspace"
        mock_boto3_client.head_bucket.assert_called_once()
    
    def test_bucket_creation_if_not_exists(self, mock_boto3_client):
        """Test bucket creation when it doesn't exist."""
        # Simulate bucket not found
        error_response = {'Error': {'Code': '404'}}
        mock_boto3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
        mock_boto3_client.create_bucket.return_value = {}
        
        client = StorageClient()
        
        mock_boto3_client.create_bucket.assert_called_once()
    
    def test_generate_presigned_put_url(self, mock_boto3_client):
        """Test generating presigned PUT URL."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.generate_presigned_url.return_value = "https://minio/presigned-put"
        
        client = StorageClient()
        url = client.generate_presigned_put_url("test/object.txt")
        
        assert url == "https://minio/presigned-put"
        mock_boto3_client.generate_presigned_url.assert_called_once_with(
            'put_object',
            Params={'Bucket': 'dataspace', 'Key': 'test/object.txt'},
            ExpiresIn=3600
        )
    
    def test_generate_presigned_put_url_with_content_type(self, mock_boto3_client):
        """Test generating presigned PUT URL with content type."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.generate_presigned_url.return_value = "https://minio/presigned-put"
        
        client = StorageClient()
        url = client.generate_presigned_put_url("test/object.txt", content_type="text/plain")
        
        assert url == "https://minio/presigned-put"
        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert call_args[1]['Params']['ContentType'] == "text/plain"
    
    def test_generate_presigned_get_url(self, mock_boto3_client):
        """Test generating presigned GET URL."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.generate_presigned_url.return_value = "https://minio/presigned-get"
        
        client = StorageClient()
        url = client.generate_presigned_get_url("test/object.txt")
        
        assert url == "https://minio/presigned-get"
        mock_boto3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': 'dataspace', 'Key': 'test/object.txt'},
            ExpiresIn=3600
        )
    
    def test_generate_presigned_get_url_with_filename(self, mock_boto3_client):
        """Test generating presigned GET URL with filename."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.generate_presigned_url.return_value = "https://minio/presigned-get"
        
        client = StorageClient()
        url = client.generate_presigned_get_url("test/object.txt", filename="download.txt")
        
        assert url == "https://minio/presigned-get"
        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert 'ResponseContentDisposition' in call_args[1]['Params']
        assert 'download.txt' in call_args[1]['Params']['ResponseContentDisposition']
    
    def test_upload_file(self, mock_boto3_client):
        """Test direct file upload."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.upload_fileobj.return_value = None
        
        client = StorageClient()
        
        from io import BytesIO
        file_data = BytesIO(b"test data")
        
        result = client.upload_file("test/object.txt", file_data)
        
        assert result is True
        mock_boto3_client.upload_fileobj.assert_called_once()
    
    def test_upload_file_with_content_type(self, mock_boto3_client):
        """Test direct file upload with content type."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.upload_fileobj.return_value = None
        
        client = StorageClient()
        
        from io import BytesIO
        file_data = BytesIO(b"test data")
        
        result = client.upload_file("test/object.txt", file_data, content_type="text/plain")
        
        assert result is True
        call_args = mock_boto3_client.upload_fileobj.call_args
        assert call_args[1]['ExtraArgs']['ContentType'] == "text/plain"
    
    def test_upload_file_failure(self, mock_boto3_client):
        """Test file upload failure."""
        mock_boto3_client.head_bucket.return_value = {}
        error_response = {'Error': {'Code': '500'}}
        mock_boto3_client.upload_fileobj.side_effect = ClientError(error_response, 'UploadFileobj')
        
        client = StorageClient()
        
        from io import BytesIO
        file_data = BytesIO(b"test data")
        
        result = client.upload_file("test/object.txt", file_data)
        
        assert result is False
    
    def test_get_object_metadata(self, mock_boto3_client):
        """Test getting object metadata."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.head_object.return_value = {
            'ContentLength': 1024,
            'ContentType': 'text/plain',
            'LastModified': 'timestamp',
            'ETag': '"abc123"'
        }
        
        client = StorageClient()
        metadata = client.get_object_metadata("test/object.txt")
        
        assert metadata['size'] == 1024
        assert metadata['content_type'] == 'text/plain'
        assert metadata['etag'] == 'abc123'
    
    def test_get_object_metadata_not_found(self, mock_boto3_client):
        """Test getting metadata for non-existent object."""
        mock_boto3_client.head_bucket.return_value = {}
        error_response = {'Error': {'Code': '404'}}
        mock_boto3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        client = StorageClient()
        metadata = client.get_object_metadata("test/nonexistent.txt")
        
        assert metadata is None
    
    def test_delete_object(self, mock_boto3_client):
        """Test deleting object."""
        mock_boto3_client.head_bucket.return_value = {}
        mock_boto3_client.delete_object.return_value = {}
        
        client = StorageClient()
        result = client.delete_object("test/object.txt")
        
        assert result is True
        mock_boto3_client.delete_object.assert_called_once()
    
    def test_get_storage_client_singleton(self, mock_boto3_client):
        """Test that get_storage_client returns singleton."""
        mock_boto3_client.head_bucket.return_value = {}
        
        # Clear any existing instance
        import src.storage.client
        src.storage.client._storage_client = None
        
        client1 = get_storage_client()
        client2 = get_storage_client()
        
        assert client1 is client2
