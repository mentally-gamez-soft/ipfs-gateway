import os
import secrets
import hashlib
from typing import Optional, Tuple
from datetime import datetime

from sqlmodel import select

from core.models.db import User, UserStatus
from core.models.connection import get_session


def _generate_salt(length: int = 16) -> str:
    return secrets.token_hex(length)


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", api_key.encode(), bytes.fromhex(salt), 200_000)
    return dk.hex()


def verify_api_key(api_key: str, api_key_hash: str, salt: Optional[str]) -> bool:
    if not salt:
        return False
    return hash_api_key(api_key, salt) == api_key_hash


def _get_user_by_email(email: str) -> Optional[User]:
    for session in get_session():
        stmt = select(User).where(User.email == email)
        return session.exec(stmt).first()
    return None


def _get_user_by_api_key(api_key: str) -> Optional[User]:
    for session in get_session():
        stmt = select(User)
        users = session.exec(stmt).all()
        for u in users:
            if u.api_key_salt and verify_api_key(api_key, u.api_key_hash, u.api_key_salt):
                return u
    return None


def register_user(email: str) -> Tuple[User, str]:
    existing = _get_user_by_email(email)
    if existing:
        raise ValueError("user_exists")
    api_key = generate_api_key()
    salt = _generate_salt()
    api_key_hash = hash_api_key(api_key, salt)
    user = User(email=email, api_key_hash=api_key_hash, api_key_salt=salt, status=UserStatus.ACTIVE)
    for session in get_session():
        session.add(user)
        session.commit()
        session.refresh(user)
        return user, api_key
    raise RuntimeError("db_session_unavailable")


def status_for_api_key(api_key: str) -> Optional[dict]:
    user = _get_user_by_api_key(api_key)
    if not user:
        return None
    for session in get_session():
        user.last_activity_at = datetime.utcnow()
        session.add(user)
        session.commit()
    return {"email": user.email, "status": user.status.value}


def revoke_user(email: str) -> bool:
    user = _get_user_by_email(email)
    if not user:
        return False
    for session in get_session():
        user.status = UserStatus.REVOKED
        session.add(user)
        session.commit()
        return True
    return False


def reactivate_user(email: str) -> bool:
    user = _get_user_by_email(email)
    if not user:
        return False
    for session in get_session():
        user.status = UserStatus.ACTIVE
        session.add(user)
        session.commit()
        return True
    return False


def renew_api_key(email: str) -> Optional[str]:
    user = _get_user_by_email(email)
    if not user:
        return None
    if user.status == UserStatus.REVOKED:
        return None
    api_key = generate_api_key()
    salt = _generate_salt()
    api_key_hash = hash_api_key(api_key, salt)
    for session in get_session():
        user.api_key_hash = api_key_hash
        user.api_key_salt = salt
        user.status = UserStatus.ACTIVE
        session.add(user)
        session.commit()
        return api_key
    return None
