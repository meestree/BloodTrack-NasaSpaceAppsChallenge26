"""SQLite users and revocable sessions; SQL values are parameterized."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class DuplicateUsername(Exception):
    """The normalized username is already registered."""


class AuthStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS auth_sessions_expiry
                    ON auth_sessions(expires_at);
            """)

    def create_user(self, username: str, password_hash: str) -> dict:
        with self.connection() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
            except sqlite3.IntegrityError as error:
                raise DuplicateUsername from error
            return {"id": cursor.lastrowid, "username": username}

    def find_user(self, username: str) -> sqlite3.Row | None:
        with self.connection() as connection:
            return connection.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

    def create_session(self, token_hash: str, user_id: int, expires_at: int, now: int) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
            connection.execute(
                "INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, expires_at),
            )

    def session_user(self, token_hash: str, now: int) -> sqlite3.Row | None:
        with self.connection() as connection:
            return connection.execute(
                """SELECT users.id, users.username FROM auth_sessions
                   JOIN users ON users.id = auth_sessions.user_id
                   WHERE token_hash = ? AND expires_at > ?""",
                (token_hash, now),
            ).fetchone()

    def delete_session(self, token_hash: str) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
