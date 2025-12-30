import os
import secrets
import hashlib
import logging
from typing import Optional, Tuple
from datetime import datetime

from sqlmodel import select

from core.models.db import User, UserStatus
from core.models.connection import get_session

logger = logging.getLogger(__name__)


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
        logger.warning(f"Attempt to register existing user: {email}")
        raise ValueError("user_exists")
    api_key = generate_api_key()
    salt = _generate_salt()
    api_key_hash = hash_api_key(api_key, salt)
    user = User(email=email, api_key_hash=api_key_hash, api_key_salt=salt, status=UserStatus.ACTIVE)
    for session in get_session():
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"User registered successfully: {email}")
        return user, api_key
    logger.error(f"Failed to register user: {email} - DB session unavailable")
    raise RuntimeError("db_session_unavailable")


def status_for_api_key(api_key: str) -> Optional[dict]:
    user = _get_user_by_api_key(api_key)
    if not user:
        logger.warning(f"Status check with invalid API key")
        return None
    for session in get_session():
        user.last_activity_at = datetime.utcnow()
        session.add(user)
        session.commit()
    logger.info(f"Status check for user: {user.email} - status: {user.status.value}")
    return {"email": user.email, "status": user.status.value}


def revoke_user(email: str) -> bool:
    user = _get_user_by_email(email)
    if not user:
        logger.warning(f"Attempt to revoke non-existent user: {email}")
        return False
    for session in get_session():
        user.status = UserStatus.REVOKED
        session.add(user)
        session.commit()
        logger.warning(f"User revoked: {email}")
        return True
    return False


def reactivate_user(email: str) -> bool:
    user = _get_user_by_email(email)
    if not user:
        logger.warning(f"Attempt to reactivate non-existent user: {email}")
        return False
    for session in get_session():
        user.status = UserStatus.ACTIVE
        session.add(user)
        session.commit()
        logger.info(f"User reactivated: {email}")
        return True
    return False


def renew_api_key(email: str) -> Optional[str]:
    user = _get_user_by_email(email)
    if not user:
        logger.warning(f"Attempt to renew API key for non-existent user: {email}")
        return None
    if user.status == UserStatus.REVOKED:
        logger.warning(f"Attempt to renew API key for revoked user: {email}")
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
        logger.info(f"API key renewed for user: {email}")
        return api_key
    logger.error(f"Failed to renew API key for user: {email}")
    return None
