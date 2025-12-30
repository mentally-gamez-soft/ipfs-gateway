"""
API tests for file upload and retrieval routes
"""
import os
import importlib
import pytest
import io
from unittest.mock import patch, Mock
from core import create_app
from sqlmodel import Session
from core.models.db import User, UserStatus, File, AuditLog
from core.services.auth_service import generate_api_key, hash_api_key
from core.models.connection import get_session


@pytest.fixture
def app(monkeypatch):
    """Create test Flask app with in-memory SQLite"""
    # Set test database URL BEFORE creating app
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("FILEBASE_IPFS_API_KEY", "test-api-key")
    monkeypatch.setenv("FILEBASE_BUCKET", "test-bucket")
    monkeypatch.setenv("ADMIN_API_KEY", "admin-key")
    
    # Reload settings to pick up new environment variables
    import core.config.settings as settings
    importlib.reload(settings)
    
    # Create app (will initialize DB with test SQLite)
    app = create_app("testing")
    app.config["TESTING"] = True
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Create database session using the same connection as the app"""
    # Use get_session() which uses the global engine initialized by the app
    for session in get_session():
        yield session


@pytest.fixture
def api_key(app, db_session):
    """Create test API key and user"""
    import secrets
    api_key = generate_api_key()
    salt = secrets.token_hex(16)
    hashed_key = hash_api_key(api_key, salt)
    
    user = User(
        email="test@example.com",
        api_key_hash=hashed_key,
        api_key_salt=salt,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    
    return api_key


class TestUploadRoute:
    """Tests for POST /upload endpoint"""

    @patch("core.routes.upload.filebase_service.upload_to_filebase")
    def test_upload_success(self, mock_upload, client, api_key):
        """Should successfully upload file"""
        mock_upload.return_value = ("etag123", "QmTest123", "text/plain")
        
        file_data = {
            "file": (io.BytesIO(b"test content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["cid"] == "QmTest123"
        assert data["filename"] == "test.txt"
        assert data["mime_type"] == "text/plain"

    def test_upload_missing_file(self, client, api_key):
        """Should return 400 if file not provided"""
        response = client.post(
            "/upload",
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "missing_file"

    def test_upload_empty_filename(self, client, api_key):
        """Should return 400 if filename is empty"""
        file_data = {
            "file": (io.BytesIO(b"content"), "")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "empty_filename"

    def test_upload_missing_auth(self, client):
        """Should return 401 if auth header missing"""
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
        )
        
        assert response.status_code == 401


class TestRetrieveRoute:
    """Tests for GET /retrieve/<cid> endpoint"""

    @patch("core.routes.upload.filebase_service.retrieve_from_filebase")
    def test_retrieve_not_found(self, mock_retrieve, client, api_key):
        """Should return 404 for non-existent file"""
        response = client.get(
            "/retrieve/QmNotFound",
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "not_found"

    def test_retrieve_missing_auth(self, client):
        """Should return 401 if auth header missing"""
        response = client.get("/retrieve/QmTest123")
        
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
