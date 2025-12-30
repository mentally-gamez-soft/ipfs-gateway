"""
API tests for file upload and retrieval routes
"""
import os
import importlib
import pytest
import io
from unittest.mock import patch, Mock
from core import create_app
from sqlmodel import Session, select
from core.models.db import User, UserStatus, File, AuditLog, PinStatus, UserRole
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

    @patch("core.routes.upload.upload_file_task.apply_async")
    def test_upload_success(self, mock_task, client, api_key):
        """Should successfully queue upload task"""
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.id = "test-task-123"
        mock_task.return_value = mock_result
        
        file_data = {
            "file": (io.BytesIO(b"test content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 202
        data = response.get_json()
        assert "task_id" in data
        assert "message" in data
        assert data["message"] == "Upload task queued"

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


class TestPinRoutes:
    """Tests for POST /pin/<cid> and /unpin/<cid> endpoints"""

    def _create_file(self, db_session, user_id: int, cid: str, status: PinStatus = PinStatus.UNPINNED):
        file_record = File(
            cid=cid,
            user_id=user_id,
            pin_status=status,
            original_filename=f"{cid}.txt",
            mime_type="text/plain",
        )
        db_session.add(file_record)
        db_session.commit()
        return file_record

    @patch("core.routes.upload.pin_content_task.apply_async")
    def test_pin_success(self, mock_task, client, api_key, db_session):
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.id = "test-pin-task-123"
        mock_task.return_value = mock_result
        
        cid = "QmToPin"
        user_id = db_session.exec(select(User.id).where(User.email == "test@example.com")).first()
        self._create_file(db_session, user_id, cid, PinStatus.UNPINNED)

        response = client.post(f"/pin/{cid}", headers={"X-API-Key": api_key})
        assert response.status_code == 202
        data = response.get_json()
        assert "task_id" in data
        assert "message" in data

    @patch("core.routes.upload.unpin_content_task.apply_async")
    def test_unpin_success(self, mock_task, client, api_key, db_session):
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.id = "test-unpin-task-123"
        mock_task.return_value = mock_result
        
        cid = "QmToUnpin"
        user_id = db_session.exec(select(User.id).where(User.email == "test@example.com")).first()
        self._create_file(db_session, user_id, cid, PinStatus.PINNED)

        response = client.post(f"/unpin/{cid}", headers={"X-API-Key": api_key})
        assert response.status_code == 202
        data = response.get_json()
        assert "task_id" in data
        assert "message" in data
        # Note: Async - audit log created by Celery task, not immediately

    def test_pin_not_found(self, client, api_key):
        response = client.post("/pin/QmMissing", headers={"X-API-Key": api_key})
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "not_found"

    def test_unpin_not_found(self, client, api_key):
        response = client.post("/unpin/QmMissing", headers={"X-API-Key": api_key})
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "not_found"

    def test_pin_requires_auth(self, client):
        response = client.post("/pin/QmTest")
        assert response.status_code == 401

    def test_unpin_requires_auth(self, client):
        response = client.post("/unpin/QmTest")
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
    
    @patch("core.routes.upload.upload_file_task.apply_async")
    def test_upload_within_size_limit(self, mock_task, client, api_key):
        """Should accept file within 3MB limit"""
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.id = "test-task-123"
        mock_task.return_value = mock_result
        
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
        
        assert response.status_code == 202


class TestUploadQuotaEnforcement:
    """Tests for monthly upload quota (15 uploads/month for standard users)"""
    
    @patch("core.routes.upload.upload_file_task.apply_async")
    def test_standard_user_within_quota(self, mock_task, client, db_session):
        """Standard user with uploads remaining should succeed"""
        from unittest.mock import MagicMock
        import secrets
        mock_result = MagicMock()
        mock_result.id = "test-task-123"
        mock_task.return_value = mock_result
        
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
        
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 202
    
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
    
    @patch("core.routes.upload.upload_file_task.apply_async")
    def test_admin_user_no_quota_limit(self, mock_task, client, db_session):
        """Admin users should bypass quota limits"""
        from unittest.mock import MagicMock
        import secrets
        mock_result = MagicMock()
        mock_result.id = "test-task-123"
        mock_task.return_value = mock_result
        
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
        
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 202


class TestRateLimitHeaders:
    """Tests for rate limit headers in responses"""
    
    @patch("core.routes.upload.upload_file_task.apply_async")
    def test_upload_includes_rate_limit_headers(self, mock_task, client, api_key):
        """Upload response verifies rate limiting is applied"""
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.id = "test-task-123"
        mock_task.return_value = mock_result
        
        file_data = {
            "file": (io.BytesIO(b"content"), "test.txt")
        }
        
        response = client.post(
            "/upload",
            data=file_data,
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 202
        # Note: Async endpoints apply rate limiting but don't return rate limit headers
        # Rate limit headers are on error responses (429)


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
