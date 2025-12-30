import os
import importlib

import pytest
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool

from core import create_app


@pytest.fixture()
def client(monkeypatch):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["ADMIN_API_KEY"] = "admin-secret"
    import core.config.settings as settings
    importlib.reload(settings)
    
    # Create app first (this will call init_db)
    app = create_app()
    app.config["TESTING"] = True
    
    # Now override the global engine in core.models.connection
    import core.models.connection as connection
    connection.engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create tables with the new engine
    SQLModel.metadata.create_all(connection.engine)
    
    with app.test_client() as c:
        yield c


def test_register_and_status_and_renew(client):
    # register
    r = client.post("/register", json={"email": "one@example.com"})
    assert r.status_code == 201
    api_key = r.get_json()["api_key"]
    # status
    s = client.post("/status", headers={"X-API-Key": api_key})
    assert s.status_code == 200
    # renew
    rn = client.post("/renew", json={"email": "one@example.com"})
    assert rn.status_code == 200
    new_key = rn.get_json()["api_key"]
    assert new_key != api_key


def test_revoke_and_reactivate_admin_only(client):
    client.post("/register", json={"email": "two@example.com"})
    # missing admin key
    rv = client.post("/revoke", json={"email": "two@example.com"})
    assert rv.status_code == 403
    # with admin key
    rv = client.post("/revoke", headers={"X-Admin-Key": "admin-secret"}, json={"email": "two@example.com"})
    assert rv.status_code == 200
    ac = client.post("/reactivate", headers={"X-Admin-Key": "admin-secret"}, json={"email": "two@example.com"})
    assert ac.status_code == 200
