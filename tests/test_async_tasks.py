"""
Tests for async task functionality (Celery + Redis).

These tests focus on endpoint behavior and task status tracking.
Actual Celery task execution is mocked to avoid Redis dependency in tests.
"""
import os
import pytest
import json
import io
import importlib
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session

from core import create_app
from core.models.db import User, File, TaskStatus, TaskState, PinStatus


@pytest.fixture()
def client():
    """Test client with in-memory SQLite database."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["ADMIN_API_KEY"] = "admin-secret"
    os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
    os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"
    
    import core.config.settings as settings
    importlib.reload(settings)

    app = create_app()
    app.config["TESTING"] = True

    # Override global engine
    import core.models.connection as connection
    connection.engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(connection.engine)

    with app.test_client() as client:
        yield client


@pytest.fixture
def test_db():
    """Create an in-memory SQLite test database."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestAsyncUploadEndpoint:
    """Test async upload endpoint behavior."""
    
    def test_upload_queues_task(self, client):
        """Test upload endpoint queues Celery task and returns task_id."""
        from core.services.auth_service import register_user
        
        # Register user
        user, api_key = register_user("test@example.com")
        
        # Mock Celery task
        with patch('core.routes.upload.upload_file_task.apply_async') as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-celery-task-123"
            mock_task.return_value = mock_result
            
            # Upload file
            response = client.post(
                "/upload",
                data={"file": (io.BytesIO(b"test content"), "test.txt")},
                headers={"X-API-Key": api_key},
                content_type="multipart/form-data"
            )
            
            assert response.status_code == 202
            data = response.json
            assert "task_id" in data
            assert "message" in data
            assert data["message"] == "Upload task queued"


class TestAsyncPinEndpoint:
    """Test async pin/unpin endpoint behavior."""
    
    def test_pin_queues_task(self, client):
        """Test pin endpoint queues Celery task."""
        from core.services.auth_service import register_user
        from core.models.connection import get_session
        
        # Register user and create file
        user, api_key = register_user("test@example.com")
        
        for session in get_session():
            from sqlmodel import select
            stmt = select(User).where(User.email == "test@example.com")
            user = session.exec(stmt).first()
            
            file_record = File(
                cid="QmTest123",
                user_id=user.id,
                original_filename="test.txt",
                pin_status=PinStatus.UNPINNED
            )
            session.add(file_record)
            session.commit()
            break
        
        # Mock Celery task
        with patch('core.routes.upload.pin_content_task.apply_async') as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-pin-task-123"
            mock_task.return_value = mock_result
            
            response = client.post(
                "/pin/QmTest123",
                headers={"X-API-Key": api_key}
            )
            
            assert response.status_code == 202
            data = response.json
            assert "task_id" in data
            assert "message" in data
    
    def test_unpin_queues_task(self, client):
        """Test unpin endpoint queues Celery task."""
        from core.services.auth_service import register_user
        from core.models.connection import get_session
        
        # Register user and create file
        user, api_key = register_user("test@example.com")
        
        for session in get_session():
            from sqlmodel import select
            stmt = select(User).where(User.email == "test@example.com")
            user = session.exec(stmt).first()
            
            file_record = File(
                cid="QmTest456",
                user_id=user.id,
                original_filename="test.txt",
                pin_status=PinStatus.PINNED
            )
            session.add(file_record)
            session.commit()
            break
        
        # Mock Celery task
        with patch('core.routes.upload.unpin_content_task.apply_async') as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-unpin-task-123"
            mock_task.return_value = mock_result
            
            response = client.post(
                "/unpin/QmTest456",
                headers={"X-API-Key": api_key}
            )
            
            assert response.status_code == 202
            data = response.json
            assert "task_id" in data
            assert "message" in data


class TestTaskStatusEndpoint:
    """Test task status retrieval endpoint."""
    
    def test_get_task_status_success(self, client):
        """Test retrieving task status."""
        from core.services.auth_service import register_user
        from core.models.connection import get_session
        
        # Register user
        user, api_key = register_user("test@example.com")
        
        # Create task status
        for session in get_session():
            from sqlmodel import select
            stmt = select(User).where(User.email == "test@example.com")
            user = session.exec(stmt).first()
            
            task_status = TaskStatus(
                task_id="test-task-status-123",
                user_id=user.id,
                task_type="upload",
                state=TaskState.SUCCESS,
                result=json.dumps({"cid": "QmTest123"})
            )
            session.add(task_status)
            session.commit()
            break
        
        # Request task status
        response = client.get(
            "/task/test-task-status-123",
            headers={"X-API-Key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json
        assert data["task_id"] == "test-task-status-123"
        assert data["state"] == "success"  # Enum value is lowercase
        assert "result" in data
    
    def test_get_task_status_not_found(self, client):
        """Test retrieving non-existent task."""
        from core.services.auth_service import register_user
        
        user, api_key = register_user("test@example.com")
        
        response = client.get(
            "/task/nonexistent-task",
            headers={"X-API-Key": api_key}
        )
        
        assert response.status_code == 404
    
    def test_get_task_status_unauthorized(self, client):
        """Test accessing another user's task."""
        from core.models.connection import get_session
        from core.services.auth_service import register_user
        from sqlmodel import select
        
        # Register two users
        user1, api_key1 = register_user("user1@example.com")
        user2, api_key2 = register_user("user2@example.com")
        
        # Create task for user1
        for session in get_session():
            stmt = select(User).where(User.email == "user1@example.com")
            user1 = session.exec(stmt).first()
            
            task_status = TaskStatus(
                task_id="user1-task-123",
                user_id=user1.id,
                task_type="upload",
                state=TaskState.PENDING
            )
            session.add(task_status)
            session.commit()
            break
        
        # Try to access with user2's API key
        response = client.get(
            "/task/user1-task-123",
            headers={"X-API-Key": api_key2}
        )
        
        assert response.status_code == 404  # Not found for security


class TestTaskStatusModel:
    """Test TaskStatus model creation and state tracking."""
    
    def test_create_task_status(self, test_db):
        """Test creating a task status record."""
        user = User(
            email="test@example.com",
            api_key_hash="hash123"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        task_status = TaskStatus(
            task_id="test-task-123",
            user_id=user.id,
            task_type="upload",
            state=TaskState.PENDING
        )
        test_db.add(task_status)
        test_db.commit()
        test_db.refresh(task_status)
        
        assert task_status.id is not None
        assert task_status.task_id == "test-task-123"
        assert task_status.state == TaskState.PENDING
        assert task_status.created_at is not None
    
    def test_update_task_status(self, test_db):
        """Test updating task status state."""
        user = User(
            email="test@example.com",
            api_key_hash="hash123"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        task_status = TaskStatus(
            task_id="test-task-456",
            user_id=user.id,
            task_type="upload",
            state=TaskState.PENDING
        )
        test_db.add(task_status)
        test_db.commit()
        test_db.refresh(task_status)
        
        # Update to SUCCESS
        task_status.state = TaskState.SUCCESS
        task_status.result = json.dumps({"cid": "QmTest123"})
        test_db.commit()
        test_db.refresh(task_status)
        
        assert task_status.state == TaskState.SUCCESS
        assert json.loads(task_status.result)["cid"] == "QmTest123"
        assert task_status.updated_at is not None
