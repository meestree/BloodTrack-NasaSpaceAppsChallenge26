import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "astronautas.db"
    schema = (Path(__file__).parent / "fixtures" / "astronautas.sql").read_text()
    with sqlite3.connect(path) as connection:
        connection.executescript(schema)
    return path


@pytest.fixture
def client(database_path: Path):
    with TestClient(create_app(database_path)) as test_client:
        yield test_client


@pytest.fixture
def frontend_requests(client, monkeypatch):
    """Adapt the real FastAPI responses to the frontend's requests transport."""
    requests = pytest.importorskip('requests')
    from urllib.parse import urlsplit
    from frontend import api

    calls = []
    def send(method, url, **kwargs):
        path = urlsplit(url).path
        calls.append((method, path, kwargs.get('params', {})))
        kwargs.pop('timeout', None)
        result = client.request(method, path, **kwargs)
        response = requests.Response()
        response.status_code = result.status_code
        response._content = result.content
        response.headers.update(result.headers)
        return response

    monkeypatch.setattr(api.requests, 'request', send)
    return calls
