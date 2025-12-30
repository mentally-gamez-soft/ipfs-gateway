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
from core.models.db import User, UserStatus, UserRole, File, AuditLog
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


class TestFileSizeValidation:
    """Tests for file size limit enforcement (3MB max)"""
    
    def test_upload_exceeds_size_limit(self, client, api_key):
        """Should return 413 if file exceeds 3MB limit"""
        # Create a file larger than 3MB
        large_content = b"x" * (3 * 1024 * 1024 + 1)  # 3MB + 1 byte
        file_data = {
            "file": (io.BytesIO(large_content), "large.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 413
        data = response.get_json()
        assert "file_too_large" in data["error"]
    
    @patch("core.routes.upload.filebase_service.upload_to_filebase")
    def test_upload_within_size_limit(self, mock_upload, client, api_key):
        """Should accept file within 3MB limit"""
        mock_upload.return_value = ("etag123", "QmTest123", "text/plain")
        
        # Create a file under 3MB
        content = b"x" * (2 * 1024 * 1024)  # 2MB
        file_data = {
            "file": (io.BytesIO(content), "valid.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 201


class TestUploadQuotaEnforcement:
    """Tests for monthly upload quota (15 uploads/month for standard users)"""
    
    @patch("core.routes.upload.filebase_service.upload_to_filebase")
    def test_standard_user_within_quota(self, mock_upload, client, db_session):
        """Standard user with uploads remaining should succeed"""
        import secrets
        api_key = generate_api_key()
        salt = secrets.token_hex(16)
        hashed_key = hash_api_key(api_key, salt)
        
        user = User(
            email="standard@example.com",
            api_key_hash=hashed_key,
            api_key_salt=salt,
            status=UserStatus.ACTIVE,
            role=UserRole.STANDARD,
            upload_count=5,
        )
        db_session.add(user)
        db_session.commit()
        
        mock_upload.return_value = ("etag123", "QmTest123", "text/plain")
        
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 201
    
    def test_standard_user_quota_exceeded(self, client, db_session):
        """Standard user exceeding 15 uploads should get 429"""
        import secrets
        api_key = generate_api_key()
        salt = secrets.token_hex(16)
        hashed_key = hash_api_key(api_key, salt)
        
        user = User(
            email="maxed@example.com",
            api_key_hash=hashed_key,
            api_key_salt=salt,
            status=UserStatus.ACTIVE,
            role=UserRole.STANDARD,
            upload_count=15,
        )
        db_session.add(user)
        db_session.commit()
        
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 429
        data = response.get_json()
        assert "quota_exceeded" in data["error"]
        assert "reset_date" in data
    
    @patch("core.routes.upload.filebase_service.upload_to_filebase")
    def test_admin_user_no_quota_limit(self, mock_upload, client, db_session):
        """Admin users should bypass quota limits"""
        import secrets
        api_key = generate_api_key()
        salt = secrets.token_hex(16)
        hashed_key = hash_api_key(api_key, salt)
        
        user = User(
            email="admin@example.com",
            api_key_hash=hashed_key,
            api_key_salt=salt,
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
            upload_count=100,  # Way over limit
        )
        db_session.add(user)
        db_session.commit()
        
        mock_upload.return_value = ("etag123", "QmTest123", "text/plain")
        
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 201


class TestRateLimitHeaders:
    """Tests for rate limit headers in responses"""
    
    @patch("core.routes.upload.filebase_service.upload_to_filebase")
    def test_upload_includes_rate_limit_headers(self, mock_upload, client, api_key):
        """Upload response should include rate limit headers"""
        mock_upload.return_value = ("etag123", "QmTest123", "text/plain")
        
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 201
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


class TestOwnershipValidation:
    """Tests for file ownership enforcement on retrieve"""
    
    @patch("core.routes.upload.filebase_service.retrieve_from_filebase")
    def test_retrieve_own_file_success(self, mock_retrieve, client, db_session, api_key):
        """User should retrieve their own file"""
        # Get user from db
        from sqlmodel import select
        stmt = select(User).where(User.email == "test@example.com")
        user = db_session.exec(stmt).first()
        
        # Create file owned by user
        file = File(
            cid="QmOwnFile123",
            user_id=user.id,
            original_filename="myfile.txt",
            mime_type="text/plain"
        )
        db_session.add(file)
        db_session.commit()
        
        mock_retrieve.return_value = b"file content"
        
        response = client.get(
            "/retrieve/QmOwnFile123",
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 200
    
    @patch("core.routes.upload.filebase_service.retrieve_from_filebase")
    def test_retrieve_others_file_forbidden(self, mock_retrieve, client, db_session, api_key):
        """User should NOT retrieve someone else's file"""
        # Create another user
        import secrets
        other_salt = secrets.token_hex(16)
        other_user = User(
            email="other@example.com",
            api_key_hash=hash_api_key("other-key", other_salt),
            api_key_salt=other_salt,
            status=UserStatus.ACTIVE,
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create file owned by other user
        file = File(
            cid="QmOtherFile123",
            user_id=other_user.id,
            original_filename="notmine.txt",
            mime_type="text/plain"
        )
        db_session.add(file)
        db_session.commit()
        
        response = client.get(
            "/retrieve/QmOtherFile123",
            headers={"X-API-Key": api_key},
        )
        
        # Return 404 to not reveal file existence
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "not_found"
    
    @patch("core.routes.upload.filebase_service.retrieve_from_filebase")
    def test_admin_retrieve_any_file(self, mock_retrieve, client, db_session):
        """Admin users should retrieve any file"""
        import secrets
        
        # Create admin user
        admin_key = generate_api_key()
        salt = secrets.token_hex(16)
        admin = User(
            email="admin@example.com",
            api_key_hash=hash_api_key(admin_key, salt),
            api_key_salt=salt,
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
        )
        db_session.add(admin)
        db_session.commit()
        
        # Create another user
        other_salt = secrets.token_hex(16)
        other_user = User(
            email="other@example.com",
            api_key_hash=hash_api_key("other-key", other_salt),
            api_key_salt=other_salt,
            status=UserStatus.ACTIVE,
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create file owned by other user
        file = File(
            cid="QmOtherFile456",
            user_id=other_user.id,
            original_filename="anyfile.txt",
            mime_type="text/plain"
        )
        db_session.add(file)
        db_session.commit()
        
        mock_retrieve.return_value = b"file content"
        
        response = client.get(
            "/retrieve/QmOtherFile456",
            headers={"X-API-Key": admin_key},
        )
        
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
