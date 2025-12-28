import pytest
from unittest.mock import patch, MagicMock
from core import create_app


def test_health_route():
    # Mock SQLAlchemy engine creation to avoid DB dependencies
    mock_engine = MagicMock()
    with patch('core.models.connection.create_engine', return_value=mock_engine):
        app = create_app("development")
        client = app.test_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "env" in data
