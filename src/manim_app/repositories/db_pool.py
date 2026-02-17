"""Thread-local database connection management."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from manim_app.core.config import AppConfig, get_required_env

try:
    from pysqlcipher3 import dbapi2 as sqlcipher

    SQLCIPHER_AVAILABLE = True
except ImportError:
    sqlcipher = None
    SQLCIPHER_AVAILABLE = False


class ThreadLocalConnection:
    """Maintain one DB connection per thread for SQLite/SQLCipher safety."""

    def __init__(self, config: AppConfig):
        self._config = config
        self._local = threading.local()

    def _open_connection(self) -> sqlite3.Connection:
        db_path = Path(self._config.database.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        if SQLCIPHER_AVAILABLE:
            connection = sqlcipher.connect(str(db_path), check_same_thread=False)
            key = get_required_env(self._config.database.key_env).replace("'", "''")
            connection.execute(f"PRAGMA key = '{key}'")
            connection.execute("PRAGMA cipher_compatibility = 4")
            connection.execute("PRAGMA foreign_keys = ON")
            connection.row_factory = sqlite3.Row
            return connection

        if not self._config.database.allow_sqlite_fallback:
            raise RuntimeError(
                "SQLCipher is required but unavailable. Install pysqlcipher3 or enable fallback."
            )

        connection = sqlite3.connect(str(db_path), check_same_thread=False)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def get_connection(self) -> sqlite3.Connection:
        """Return current thread's connection, creating it when needed."""
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = self._open_connection()
            self._local.connection = connection
        return connection

    def close_connection(self) -> None:
        """Close current thread's connection."""
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a query and commit the transaction."""
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return cursor

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Fetch all rows for a query."""
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Fetch first row for a query."""
        cursor = self.execute(query, params)
        return cursor.fetchone()
