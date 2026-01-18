from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class UserRole(str, PyEnum):
    STANDARD = "standard"
    ADMIN = "admin"
    PREMIUM = "premium"


class PinStatus(str, PyEnum):
    UNPINNED = "unpinned"
    PINNING = "pinning"
    PINNED = "pinned"
    UNPINNING = "unpinning"


class TaskState(str, PyEnum):
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"


class User(SQLModel, table=True):
    """User model representing gateway users."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    api_key_hash: str = Field(max_length=255)
    api_key_salt: Optional[str] = Field(default=None, max_length=255)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    role: UserRole = Field(default=UserRole.STANDARD)
    upload_count: int = Field(default=0)
    upload_quota_reset_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: Optional[datetime] = None

    # Relationships
    files: list["File"] = Relationship(back_populates="user")
    audit_logs: list["AuditLog"] = Relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, status={self.status}, role={self.role}, upload_count={self.upload_count}, created_at={self.created_at})"

class File(SQLModel, table=True):
    """File model representing uploaded content on IPFS."""
    __tablename__ = "files"

    id: Optional[int] = Field(default=None, primary_key=True)
    cid: str = Field(index=True, unique=True, max_length=255)
    user_id: int = Field(foreign_key="users.id", index=True)
    pin_status: PinStatus = Field(default=PinStatus.PINNED)
    original_filename: Optional[str] = Field(default=None, max_length=255)
    mime_type: Optional[str] = Field(default=None, max_length=100)
    file_size: Optional[int] = Field(default=None)  # Size in bytes
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    last_access_at: Optional[datetime] = None

    # Relationships
    user: User = Relationship(back_populates="files")


class AuditLog(SQLModel, table=True):
    """Audit log model for tracking API requests and actions."""
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    action: str = Field(max_length=50, index=True)
    details: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    user: User = Relationship(back_populates="audit_logs")


class TaskStatus(SQLModel, table=True):
    """Model for tracking async task status."""
    __tablename__ = "task_status"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True, unique=True, max_length=255)
    user_id: int = Field(foreign_key="users.id", index=True)
    task_type: str = Field(max_length=50)  # 'upload', 'pin', 'unpin'
    state: TaskState = Field(default=TaskState.PENDING)
    result: Optional[str] = Field(default=None)  # JSON result or error message
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"TaskStatus(task_id={self.task_id}, user_id={self.user_id}, task_type={self.task_type}, state={self.state})"
