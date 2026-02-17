"""Audit log repository."""

from __future__ import annotations

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
