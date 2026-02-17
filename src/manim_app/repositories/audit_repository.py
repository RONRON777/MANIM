"""Audit log repository."""

from __future__ import annotations

from typing import Any

from manim_app.repositories.db_pool import ThreadLocalConnection


class AuditRepository:
    """Persists and manages CRUD audit logs."""

    def __init__(self, pool: ThreadLocalConnection):
        self._pool = pool

    def add_log(self, action: str, entity: str, entity_id: int | None, detail: str) -> None:
        """Insert an audit log record."""
        self._pool.execute(
            """
            INSERT INTO audit_logs (action, entity, entity_id, detail)
            VALUES (?, ?, ?, ?)
            """,
            (action, entity, entity_id, detail),
        )

    def cleanup_old_logs(self, retention_days: int) -> int:
        """Delete logs older than retention_days and return removed row count."""
        cursor = self._pool.execute(
            """
            DELETE FROM audit_logs
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{retention_days} days",),
        )
        return cursor.rowcount

    def list_logs(
        self,
        limit: int = 200,
        offset: int = 0,
        action: str | None = None,
        entity: str | None = None,
        keyword: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """List audit logs with optional filters."""
        where_clauses: list[str] = []
        params: list[Any] = []

        if action:
            where_clauses.append("action = ?")
            params.append(action)
        if entity:
            where_clauses.append("entity = ?")
            params.append(entity)
        if keyword:
            where_clauses.append("detail LIKE ?")
            params.append(f"%{keyword.strip()}%")
        if date_from:
            where_clauses.append("date(created_at) >= date(?)")
            params.append(date_from.strip())
        if date_to:
            where_clauses.append("date(created_at) <= date(?)")
            params.append(date_to.strip())

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        rows = self._pool.fetchall(
            f"""
            SELECT id, action, entity, entity_id, detail, created_at
            FROM audit_logs
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )
        return [dict(row) for row in rows]

    def purge_all_logs(self) -> None:
        """Delete all audit logs and reset sequence."""
        self._pool.execute("DELETE FROM audit_logs")
        self._pool.execute("DELETE FROM sqlite_sequence WHERE name = 'audit_logs'")
