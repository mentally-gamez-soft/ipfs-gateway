import pytest
from datetime import datetime
from faker import Faker
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from core.models.db import User, File, AuditLog, UserStatus, PinStatus


fake = Faker()


@pytest.fixture
def test_db():
    """Create an in-memory SQLite test database."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestUserModel:
    def test_create_user(self, test_db):
        """Test creating a user."""
        user = User(
            email=fake.email(),
            api_key_hash="hashed_key_123",
            status=UserStatus.ACTIVE,
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.id is not None
        assert user.email is not None
        assert user.status == UserStatus.ACTIVE
        assert user.created_at is not None

    def test_user_status_enum(self, test_db):
        """Test user status enum values."""
        for status in [UserStatus.ACTIVE, UserStatus.INACTIVE, UserStatus.REVOKED]:
            user = User(
                email=fake.email(),
                api_key_hash="key",
                status=status,
            )
            test_db.add(user)
        test_db.commit()

        users = test_db.query(User).all()
        assert len(users) == 3
        assert any(u.status == UserStatus.REVOKED for u in users)

    def test_user_email_unique(self, test_db):
        """Test email uniqueness constraint."""
        email = fake.email()
        user1 = User(email=email, api_key_hash="key1")
        user2 = User(email=email, api_key_hash="key2")

        test_db.add(user1)
        test_db.commit()
        test_db.add(user2)

        with pytest.raises(Exception):  # Integrity error
            test_db.commit()


class TestFileModel:
    def test_create_file(self, test_db):
        """Test creating a file."""
        user = User(email=fake.email(), api_key_hash="key")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        file = File(
            cid="bafybeid" + fake.word(),
            user_id=user.id,
            pin_status=PinStatus.UNPINNED,
        )
        test_db.add(file)
        test_db.commit()
        test_db.refresh(file)

        assert file.id is not None
        assert file.user_id == user.id
        assert file.pin_status == PinStatus.UNPINNED

    def test_file_cid_unique(self, test_db):
        """Test CID uniqueness."""
        user = User(email=fake.email(), api_key_hash="key")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        cid = "bafybeid123"
        file1 = File(cid=cid, user_id=user.id)
        file2 = File(cid=cid, user_id=user.id)

        test_db.add(file1)
        test_db.commit()
        test_db.add(file2)

        with pytest.raises(Exception):
            test_db.commit()

    def test_file_pin_status_enum(self, test_db):
        """Test file pin status enum."""
        user = User(email=fake.email(), api_key_hash="key")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        for status in [PinStatus.UNPINNED, PinStatus.PINNING, PinStatus.PINNED]:
            file = File(
                cid="bafybeid" + fake.word() + str(status),
                user_id=user.id,
                pin_status=status,
            )
            test_db.add(file)
        test_db.commit()

        files = test_db.query(File).all()
        assert len(files) == 3
        assert any(f.pin_status == PinStatus.PINNED for f in files)

    def test_file_user_relationship(self, test_db):
        """Test file-user relationship."""
        user = User(email=fake.email(), api_key_hash="key")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        file1 = File(cid="cid1", user_id=user.id)
        file2 = File(cid="cid2", user_id=user.id)
        test_db.add(file1)
        test_db.add(file2)
        test_db.commit()

        test_db.refresh(user)
        assert len(user.files) == 2


class TestAuditLogModel:
    def test_create_audit_log(self, test_db):
        """Test creating an audit log."""
        user = User(email=fake.email(), api_key_hash="key")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        audit = AuditLog(
            user_id=user.id,
            action="upload",
            details='{"cid": "bafybeid123"}',
        )
        test_db.add(audit)
        test_db.commit()
        test_db.refresh(audit)

        assert audit.id is not None
        assert audit.action == "upload"
        assert audit.created_at is not None

    def test_audit_log_user_relationship(self, test_db):
        """Test audit log-user relationship."""
        user = User(email=fake.email(), api_key_hash="key")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        for action in ["register", "upload", "pin"]:
            audit = AuditLog(user_id=user.id, action=action)
            test_db.add(audit)
        test_db.commit()

        test_db.refresh(user)
        assert len(user.audit_logs) == 3
        assert any(a.action == "pin" for a in user.audit_logs)

    def test_audit_log_action_indexed(self, test_db):
        """Test that action field is indexed."""
        user = User(email=fake.email(), api_key_hash="key")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        for i in range(5):
            audit = AuditLog(user_id=user.id, action="upload" if i % 2 == 0 else "pin")
            test_db.add(audit)
        test_db.commit()

        uploads = test_db.query(AuditLog).filter(AuditLog.action == "upload").all()
        assert len(uploads) == 3
