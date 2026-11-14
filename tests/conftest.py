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
