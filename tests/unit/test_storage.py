"""Unit tests for storage module."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.storage.minio_client import MinIOStorage


class TestMinIOStorage:
    """Tests for MinIO storage client."""
    
    @patch('src.storage.minio_client.boto3.client')
    def test_storage_initialization(self, mock_boto_client):
        """Test storage client initialization."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage(
            endpoint="http://localhost:9000",
            access_key="testkey",
            secret_key="testsecret",
            bucket="testbucket"
        )
        
        assert storage.endpoint == "http://localhost:9000"
        assert storage.bucket == "testbucket"
        mock_boto_client.assert_called_once()
    
    @patch('src.storage.minio_client.boto3.client')
    def test_generate_object_key(self, mock_boto_client):
        """Test object key generation."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage()
        
        # Test with dataset_id
        key = storage.generate_object_key("test.csv", "provider-123", "dataset-456")
        assert key.startswith("datasets/provider-123/dataset-456/")
        assert key.endswith("_test.csv")
        # UUID should be full length (36 chars including hyphens)
        uuid_part = key.split("/")[-1].split("_")[0]
        assert len(uuid_part) == 36
        
        # Test without dataset_id
        key = storage.generate_object_key("test.csv", "provider-123")
        assert key.startswith("uploads/provider-123/")
        assert key.endswith("_test.csv")
    
    @patch('src.storage.minio_client.boto3.client')
    def test_get_presigned_put_url(self, mock_boto_client):
        """Test presigned PUT URL generation."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.generate_presigned_url.return_value = "https://minio.example/presigned-url"
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage()
        url = storage.get_presigned_put_url("test/key.csv", "text/csv", 3600)
        
        assert url == "https://minio.example/presigned-url"
        mock_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="put_object",
            Params={
                "Bucket": "dataspace",
                "Key": "test/key.csv",
                "ContentType": "text/csv",
            },
            ExpiresIn=3600,
        )
    
    @patch('src.storage.minio_client.boto3.client')
    def test_get_presigned_get_url(self, mock_boto_client):
        """Test presigned GET URL generation."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.generate_presigned_url.return_value = "https://minio.example/download-url"
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage()
        url = storage.get_presigned_get_url("test/key.csv", 3600)
        
        assert url == "https://minio.example/download-url"
        mock_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={
                "Bucket": "dataspace",
                "Key": "test/key.csv",
            },
            ExpiresIn=3600,
        )
    
    @patch('src.storage.minio_client.boto3.client')
    def test_object_exists(self, mock_boto_client):
        """Test object existence check."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage()
        
        # Object exists
        mock_client.head_object.return_value = {}
        assert storage.object_exists("existing/key.csv") is True
        
        # Object doesn't exist
        from botocore.exceptions import ClientError
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        assert storage.object_exists("nonexistent/key.csv") is False
    
    @patch('src.storage.minio_client.boto3.client')
    def test_delete_object(self, mock_boto_client):
        """Test object deletion."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.delete_object.return_value = {}
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage()
        result = storage.delete_object("test/key.csv")
        
        assert result is True
        mock_client.delete_object.assert_called_once()
    
    @patch('src.storage.minio_client.boto3.client')
    def test_get_object_info(self, mock_boto_client):
        """Test getting object info."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.head_object.return_value = {
            "ContentLength": 1024,
            "ContentType": "text/csv",
            "LastModified": "2023-01-01T00:00:00Z",
            "ETag": '"abc123"'
        }
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage()
        info = storage.get_object_info("test/key.csv")
        
        assert info is not None
        assert info["size"] == 1024
        assert info["content_type"] == "text/csv"
    
    @patch('src.storage.minio_client.boto3.client')
    def test_copy_object(self, mock_boto_client):
        """Test object copying."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.copy_object.return_value = {}
        mock_boto_client.return_value = mock_client
        
        storage = MinIOStorage()
        result = storage.copy_object("source/key.csv", "dest/key.csv")
        
        assert result["source_key"] == "source/key.csv"
        assert result["dest_key"] == "dest/key.csv"
        mock_client.copy_object.assert_called_once()
