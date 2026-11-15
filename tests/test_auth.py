import sqlite3
from pathlib import Path
from time import time

import pytest
from fastapi.testclient import TestClient

from backend.auth.security import hash_password, hash_token, verify_password
from backend.main import create_app

PASSWORD = "space-apps-test-password"


def register(client: TestClient, username: str = "astronaut", **overrides):
    body = {
        "nombre_usuario": username, "password": PASSWORD,
        "email": f"{username.lower()}@example.com", "fecha_nacimiento": "1995-05-21",
    }
    body.update(overrides)
    return client.post("/api/v1/auth/register", json=body)


def login(client: TestClient, username: str = "astronaut", password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"nombre_usuario": username, "password": password})


def test_registration_stores_only_salted_argon2_hash(client: TestClient) -> None:
    response = register(client)
    assert response.status_code == 201
    user = response.json()
    assert user["id_usuario"] == 1
    assert user["nombre_usuario"] == "astronaut"
    assert user["email"] == "astronaut@example.com"
    assert user["fecha_nacimiento"] == "1995-05-21"
    assert isinstance(user["edad"], int)
    assert user["creado_en"]
    assert "password" not in response.text
    with client.app.state.auth_store.connection() as connection:
        stored = connection.execute("SELECT password_hash FROM usuarios").fetchone()[0]
        age = connection.execute("SELECT edad FROM vista_usuarios").fetchone()[0]
        assert user["edad"] == age
    assert stored.startswith("$argon2id$")
    assert verify_password(PASSWORD, stored)
    assert PASSWORD not in stored
    assert hash_password(PASSWORD) != stored


def test_login_me_and_logout(client: TestClient) -> None:
    user = register(client).json()
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
    assert response.json() == user
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_duplicate_username_is_case_insensitive(client: TestClient) -> None:
    assert register(client).status_code == 201
    assert register(client, "ASTRONAUT", email="other@example.com").status_code == 409


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
    response = register(client, password=password)
    assert response.status_code == 422
    assert password not in response.text
    assert all("input" not in error for error in response.json()["detail"])


def test_sql_injection_does_not_authenticate(client: TestClient) -> None:
    register(client)
    assert login(client, username="' OR 1=1 --").status_code == 401


def test_users_and_sessions_survive_restart(database_path: Path) -> None:
    path = database_path
    with TestClient(create_app(path)) as first:
        register(first)
        token = login(first).json()["access_token"]
    with TestClient(create_app(path)) as second:
        assert login(second).status_code == 200
        assert second.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_initialization_preserves_existing_tables(database_path: Path) -> None:
    path = database_path
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO partes_corporales (id_parte, nombre) VALUES (1, 'Neck')")
        schema_before = connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    with TestClient(create_app(path)) as client:
        register(client)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT nombre FROM partes_corporales").fetchone()[0] == "Neck"
        for name, sql in schema_before:
            assert connection.execute("SELECT sql FROM sqlite_master WHERE name = ?", (name,)).fetchone()[0] == sql


def test_duplicate_email_is_case_insensitive(client: TestClient) -> None:
    assert register(client).status_code == 201
    assert register(client, "another", email="ASTRONAUT@example.com").status_code == 409


@pytest.mark.parametrize("changes", [
    {"email": "invalid"}, {"fecha_nacimiento": "1995-02-30"},
    {"fecha_nacimiento": "2999-01-01"}, {"fecha_nacimiento": 0},
    {"fecha_nacimiento": "19950521"},
])
def test_registration_validates_profile(client: TestClient, changes: dict) -> None:
    assert register(client, **changes).status_code == 422


def test_registration_requires_new_fields(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={
        "nombre_usuario": "astronaut", "password": PASSWORD,
    })
    assert response.status_code == 422


def test_login_existing_database_user(client: TestClient) -> None:
    with client.app.state.auth_store.connection() as connection:
        connection.execute(
            """INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_nacimiento)
               VALUES (?, ?, ?, ?)""",
            ("ExistingUser", hash_password(PASSWORD), "existing@example.com", "1990-01-01"),
        )
    token = login(client, "existinguser").json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["nombre_usuario"] == "ExistingUser"
    assert register(client, "existinguser", email="other@example.com").status_code == 409


def test_session_foreign_key_uses_usuarios(client: TestClient) -> None:
    with client.app.state.auth_store.connection() as connection:
        foreign_keys = connection.execute("PRAGMA foreign_key_list(auth_sessions)").fetchall()
        assert foreign_keys[0]["table"] == "usuarios"
        assert foreign_keys[0]["to"] == "id_usuario"
        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'users'").fetchone()


def test_deleting_user_revokes_session(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]
    with client.app.state.auth_store.connection() as connection:
        connection.execute("DELETE FROM usuarios")
        assert connection.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0] == 0
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_missing_database_is_not_silently_created(tmp_path: Path) -> None:
    path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        with TestClient(create_app(path)):
            pass
    assert not path.exists()


def test_incompatible_schema_fails_without_adding_tables(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
    with pytest.raises(RuntimeError, match="usuarios schema"):
        with TestClient(create_app(path)):
            pass
    with sqlite3.connect(path) as connection:
        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'auth_sessions'").fetchone()


def test_old_session_foreign_key_is_not_silently_reused(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY);
            CREATE TABLE auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                expires_at INTEGER
            );
        """)
    with pytest.raises(RuntimeError, match="incompatible schema"):
        with TestClient(create_app(database_path)):
            pass
