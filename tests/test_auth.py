import sqlite3
from pathlib import Path
from time import time

import pytest
from fastapi.testclient import TestClient

from backend.auth.security import hash_password, hash_token, verify_password
from backend.main import create_app

PASSWORD = "space-apps-test-password"


@pytest.fixture
def client(tmp_path: Path):
    with TestClient(create_app(tmp_path / "auth.db")) as test_client:
        yield test_client


def register(client: TestClient, username: str = "astronaut"):
    return client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})


def login(client: TestClient, username: str = "astronaut", password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_registration_stores_only_salted_argon2_hash(client: TestClient) -> None:
    response = register(client)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "astronaut"}
    with client.app.state.auth_store.connection() as connection:
        stored = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored.startswith("$argon2id$")
    assert verify_password(PASSWORD, stored)
    assert PASSWORD not in stored
    assert hash_password(PASSWORD) != stored


def test_login_me_and_logout(client: TestClient) -> None:
    register(client)
    response = login(client, "ASTRONAUT")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    token = response.json()["access_token"]
    assert response.json()["expires_in"] == 3600
    headers = {"Authorization": f"Bearer {token}"}
    with client.app.state.auth_store.connection() as connection:
        stored = connection.execute("SELECT token_hash FROM auth_sessions").fetchone()[0]
    assert stored == hash_token(token)
    assert stored != token
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.json() == {"id": 1, "username": "astronaut"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_duplicate_username_is_case_insensitive(client: TestClient) -> None:
    assert register(client).status_code == 201
    assert register(client, "ASTRONAUT").status_code == 409


def test_wrong_password_and_unknown_user_have_same_error(client: TestClient) -> None:
    register(client)
    wrong = login(client, password="incorrect-password")
    unknown = login(client, username="missing")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.headers["www-authenticate"] == "Bearer"
    with client.app.state.auth_store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0] == 0


@pytest.mark.parametrize("token", [None, "invalid", "' OR 1=1 --"])
def test_missing_or_invalid_token(client: TestClient, token: str | None) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 401


def test_expired_session_is_rejected(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]
    with client.app.state.auth_store.connection() as connection:
        connection.execute("UPDATE auth_sessions SET expires_at = ?", (int(time()) - 1,))
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("password", ["tiny!", "a" * 129])
def test_invalid_password_is_not_echoed(client: TestClient, password: str) -> None:
    response = client.post("/api/v1/auth/register", json={"username": "astronaut", "password": password})
    assert response.status_code == 422
    assert password not in response.text
    assert all("input" not in error for error in response.json()["detail"])


def test_sql_injection_does_not_authenticate(client: TestClient) -> None:
    register(client)
    assert login(client, username="' OR 1=1 --").status_code == 401


def test_users_and_sessions_survive_restart(tmp_path: Path) -> None:
    path = tmp_path / "auth.db"
    with TestClient(create_app(path)) as first:
        register(first)
        token = login(first).json()["access_token"]
    with TestClient(create_app(path)) as second:
        assert login(second).status_code == 200
        assert second.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_initialization_preserves_existing_tables(tmp_path: Path) -> None:
    path = tmp_path / "auth.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE measurements (value INTEGER)")
        connection.execute("INSERT INTO measurements VALUES (42)")
    with TestClient(create_app(path)) as client:
        register(client)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT value FROM measurements").fetchone()[0] == 42
