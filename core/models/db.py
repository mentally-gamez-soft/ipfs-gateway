from datetime import datetime
from enum import Enum as PyEnum
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class PinStatus(str, PyEnum):
    UNPINNED = "unpinned"
    PINNING = "pinning"
    PINNED = "pinned"
    UNPINNING = "unpinning"


class User(SQLModel, table=True):
    """User model representing gateway users."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    api_key_hash: str = Field(max_length=255)
    api_key_salt: Optional[str] = Field(default=None, max_length=255)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: Optional[datetime] = None

    # Relationships
    files: list["File"] = Relationship(back_populates="user")
    audit_logs: list["AuditLog"] = Relationship(back_populates="user")


class File(SQLModel, table=True):
    """File model representing uploaded content on IPFS."""
    __tablename__ = "files"

    id: Optional[int] = Field(default=None, primary_key=True)
    cid: str = Field(index=True, unique=True, max_length=255)
    user_id: int = Field(foreign_key="users.id", index=True)
    pin_status: PinStatus = Field(default=PinStatus.UNPINNED)
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
