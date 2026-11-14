from fastapi.testclient import TestClient
from pathlib import Path

from backend.main import create_app


def test_health_endpoint(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "test.db")) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
