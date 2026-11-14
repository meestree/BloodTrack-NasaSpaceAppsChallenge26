"""SQLite users and revocable sessions; SQL values are parameterized."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import date
from typing import Iterator


class DuplicateAccount(Exception):
    """The username or email is already registered."""


class AuthStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        # Never silently create an empty replacement for the user's database.
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(usuarios)")}
            required = {"id_usuario", "nombre_usuario", "password_hash", "email", "fecha_nacimiento", "creado_en"}
            if not required <= columns:
                raise RuntimeError("Database must contain the supplied usuarios schema")
            connection.execute("SELECT id_usuario, nombre_usuario, email, fecha_nacimiento, edad, creado_en FROM vista_usuarios LIMIT 0")
            # An old session table must not silently refer to the former users table.
            existing = connection.execute("PRAGMA foreign_key_list(auth_sessions)").fetchall()
            session_columns = {row["name"] for row in connection.execute("PRAGMA table_info(auth_sessions)")}
            if session_columns and (not {"token_hash", "id_usuario", "expires_at"} <= session_columns or not any(
                row["table"] == "usuarios" and row["from"] == "id_usuario" and row["to"] == "id_usuario"
                for row in existing
            )):
                raise RuntimeError("auth_sessions has an incompatible schema; migrate it before starting")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario)
                        ON UPDATE CASCADE ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS auth_sessions_expiry
                    ON auth_sessions(expires_at);
            """)

    def create_user(self, username: str, password_hash: str, email: str, birth_date: date) -> sqlite3.Row:
        with self.connection() as connection:
            # Serialize duplicate checks because the supplied UNIQUE columns
            # use case-sensitive collation, while API identities do not.
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                """SELECT 1 FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE
                   OR email = ? COLLATE NOCASE""", (username, email),
            ).fetchone()
            if duplicate:
                raise DuplicateAccount
            try:
                cursor = connection.execute(
                    """INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_nacimiento)
                       VALUES (?, ?, ?, ?)""",
                    (username, password_hash, email, birth_date.isoformat()),
                )
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                    raise DuplicateAccount from error
                raise
            return connection.execute(
                "SELECT * FROM vista_usuarios WHERE id_usuario = ?", (cursor.lastrowid,),
            ).fetchone()

    def find_user(self, username: str) -> sqlite3.Row | None:
        with self.connection() as connection:
            return connection.execute(
                "SELECT id_usuario, password_hash FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE",
                (username,),
            ).fetchone()

    def create_session(self, token_hash: str, user_id: int, expires_at: int, now: int) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
            connection.execute(
                "INSERT INTO auth_sessions (token_hash, id_usuario, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, expires_at),
            )

    def session_user(self, token_hash: str, now: int) -> sqlite3.Row | None:
        with self.connection() as connection:
            return connection.execute(
                """SELECT vista_usuarios.* FROM auth_sessions
                   JOIN vista_usuarios ON vista_usuarios.id_usuario = auth_sessions.id_usuario
                   WHERE token_hash = ? AND expires_at > ?""",
                (token_hash, now),
            ).fetchone()

    def delete_session(self, token_hash: str) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
