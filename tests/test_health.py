from core import create_app


def test_health_route():
    app = create_app("development")
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "env" in data
