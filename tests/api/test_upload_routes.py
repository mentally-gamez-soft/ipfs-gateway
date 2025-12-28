"""
API tests for file upload and retrieval routes
"""
import pytest
import io
from unittest.mock import patch, Mock
from core import create_app
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from core.models.db import User, UserStatus, File, AuditLog
from core.services.auth_service import generate_api_key, hash_api_key


@pytest.fixture
def app():
    """Create test Flask app with in-memory SQLite"""
    app = create_app("testing")
    
    # Override DATABASE_URL for in-memory DB
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    app.config["DB_ENGINE"] = engine
    app.config["FILEBASE_IPFS_API_KEY"] = "test-api-key"
    app.config["FILEBASE_BUCKET"] = "test-bucket"
    app.config["ADMIN_API_KEY"] = "admin-key"
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Create database session"""
    engine = app.config.get("DB_ENGINE")
    session = Session(engine)
    yield session
    session.close()


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
        mock_upload.return_value = ("QmTest123", "text/plain")
        
        file_data = {
            "file": (io.BytesIO(b"test content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"Authorization": f"Bearer {api_key}"},
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
            headers={"Authorization": f"Bearer {api_key}"},
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
            headers={"Authorization": f"Bearer {api_key}"},
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
            headers={"Authorization": f"Bearer {api_key}"},
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
