import os
import importlib

import pytest

from core.services import auth_service as svc
from core.models.db import User, UserStatus
from core import create_app


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    # reload settings so DATABASE_URL is picked up
    import core.config.settings as settings
    importlib.reload(settings)
    app = create_app()
    yield


def test_generate_and_hash_and_verify():
    api_key = svc.generate_api_key()
    assert isinstance(api_key, str) and len(api_key) >= 40
    salt = "a" * 32
    h = svc.hash_api_key(api_key, salt)
    assert isinstance(h, str) and len(h) == 64
    assert svc.verify_api_key(api_key, h, salt)


def test_register_status_and_renew():
    email = "john@example.com"
    user, key = svc.register_user(email)
    assert user.email == email
    assert user.api_key_hash and user.api_key_salt
    status = svc.status_for_api_key(key)
    assert status == {"email": email, "status": "active"}

    new_key = svc.renew_api_key(email)
    assert new_key and new_key != key
    assert svc.status_for_api_key(new_key)["status"] == "active"


def test_revoke_and_reactivate():
    email = "amy@example.com"
    user, key = svc.register_user(email)
    assert svc.revoke_user(email) is True
    # status now revoked
    st = svc.status_for_api_key(key)
    # revoked user should be blocked
    assert st is None or st["status"] != "active"
    assert svc.reactivate_user(email) is True
    # renew key to get active usable key
    renewed = svc.renew_api_key(email)
    assert renewed is not None