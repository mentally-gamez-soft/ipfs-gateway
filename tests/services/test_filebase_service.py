"""
Unit tests for filebase_service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.services import filebase_service


class TestUploadToFilebase:
    """Tests for upload_to_filebase function"""

    @patch("boto3.client")
    def test_upload_success(self, mock_boto3_client):
        """Should successfully upload file to Filebase"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        
        # Mock put_object response and circuit breaker call
        mock_client.put_object.return_value = {"ETag": '"QmTest123"'}
        
        cid, mime_type = filebase_service.upload_to_filebase(
            api_key="test-key",
            bucket="test-bucket",
            file_bytes=b"test content",
            original_filename="test.txt",
        )
        
        assert cid == "QmTest123"
        assert mime_type == "text/plain"

    @patch("boto3.client")
    def test_upload_mime_type_pdf(self, mock_boto3_client):
        """Should detect PDF MIME type"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.put_object.return_value = {"ETag": '"Qm123"'}
        
        cid, mime_type = filebase_service.upload_to_filebase(
            api_key="test-key",
            bucket="test-bucket",
            file_bytes=b"test",
            original_filename="doc.pdf",
        )
        
        assert mime_type == "application/pdf"

    @patch("boto3.client")
    def test_upload_mime_type_png(self, mock_boto3_client):
        """Should detect PNG MIME type"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.put_object.return_value = {"ETag": '"Qm123"'}
        
        cid, mime_type = filebase_service.upload_to_filebase(
            api_key="test-key",
            bucket="test-bucket",
            file_bytes=b"test",
            original_filename="image.png",
        )
        
        assert mime_type == "image/png"

    @patch("boto3.client")
    def test_upload_default_mime_type(self, mock_boto3_client):
        """Should use default MIME type for unknown extensions"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.put_object.return_value = {"ETag": '"Qm123"'}
        
        cid, mime_type = filebase_service.upload_to_filebase(
            api_key="test-key",
            bucket="test-bucket",
            file_bytes=b"test",
            original_filename="unknown.unknownext",
        )
        
        assert mime_type == "application/octet-stream"


class TestRetrieveFromFilebase:
    """Tests for retrieve_from_filebase function"""

    @patch("boto3.client")
    def test_retrieve_success(self, mock_boto3_client):
        """Should successfully retrieve file from Filebase"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        
        # Mock get_object response
        test_content = b"file content"
        mock_response = {
            "Body": Mock(read=Mock(return_value=test_content))
        }
        mock_client.get_object.return_value = mock_response
        
        content = filebase_service.retrieve_from_filebase(
            api_key="test-key",
            bucket="test-bucket",
            cid="QmTest123",
        )
        
        assert content == test_content

    @patch("boto3.client")
    def test_retrieve_not_found(self, mock_boto3_client):
        """Should raise FilebaseNotFoundError for missing files"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        
        # Mock 404 error
        from botocore.exceptions import ClientError
        error_response = {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}
        mock_client.get_object.side_effect = ClientError(error_response, "GetObject")
        
        with pytest.raises(filebase_service.FilebaseNotFoundError):
            filebase_service.retrieve_from_filebase(
                api_key="test-key",
                bucket="test-bucket",
                cid="QmMissing",
            )


class TestExceptionHandling:
    """Tests for exception classes"""

    def test_filebase_error_inheritance(self):
        """Should inherit from Exception"""
        err = filebase_service.FilebaseError("test")
        assert isinstance(err, Exception)

    def test_filebase_not_found_error_inheritance(self):
        """Should inherit from FilebaseError"""
        err = filebase_service.FilebaseNotFoundError("test")
        assert isinstance(err, filebase_service.FilebaseError)

    def test_filebase_connection_error_inheritance(self):
        """Should inherit from FilebaseError"""
        err = filebase_service.FilebaseConnectionError("test")
        assert isinstance(err, filebase_service.FilebaseError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
