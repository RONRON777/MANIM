"""Insurance repository."""

from __future__ import annotations

from typing import Any

from manim_app.models.insurance import InsuranceCreate
from manim_app.repositories.db_pool import ThreadLocalConnection


class InsuranceRepository:
    """Handles insurance persistence."""

    def __init__(self, pool: ThreadLocalConnection):
        self._pool = pool

    def create_insurance(self, payload: InsuranceCreate) -> int:
        """Insert insurance and return new id."""
        cursor = self._pool.execute(
            """
            INSERT INTO insurances (
                customer_id,
                contract_date,
                company,
                policy_number,
                product_name,
                premium,
                insured_person,
                payment_day,
                beneficiary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.customer_id,
                payload.contract_date.isoformat(),
                payload.company,
                payload.policy_number,
                payload.product_name,
                str(payload.premium),
                payload.insured_person,
                payload.payment_day,
                payload.beneficiary,
            ),
        )
        return int(cursor.lastrowid)

    def next_insurance_id(self) -> int:
        """Return the next insurance id in insertion order."""
        row = self._pool.fetchone("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM insurances")
        return int(row["next_id"]) if row else 1

    def get_insurance(self, insurance_id: int) -> dict[str, Any] | None:
        """Fetch one active insurance record."""
        row = self._pool.fetchone(
            """
            SELECT
                id,
                customer_id,
                contract_date,
                company,
                policy_number,
                product_name,
                premium,
                insured_person,
                payment_day,
                beneficiary
            FROM insurances
            WHERE id = ? AND deleted_at IS NULL
            """,
            (insurance_id,),
        )
        return dict(row) if row else None

    def list_insurances(self, customer_id: int, limit: int, offset: int) -> list[dict[str, Any]]:
        """List active insurances for a customer with pagination."""
        rows = self._pool.fetchall(
            """
            SELECT
                id,
                customer_id,
                contract_date,
                company,
                policy_number,
                product_name,
                premium,
                insured_person,
                payment_day,
                beneficiary
            FROM insurances
            WHERE customer_id = ? AND deleted_at IS NULL
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (customer_id, limit, offset),
        )
        return [dict(row) for row in rows]

    def search_insurances(self, field: str, keyword: str, limit: int, offset: int) -> list[dict[str, Any]]:
        """Search active insurances by a permitted text field."""
        allowed = {
            "id": "CAST(id AS TEXT)",
            "customer_id": "CAST(customer_id AS TEXT)",
            "company": "company",
            "policy_number": "policy_number",
            "product_name": "product_name",
            "insured_person": "insured_person",
            "beneficiary": "beneficiary",
        }
        if field not in allowed:
            raise ValueError("지원하지 않는 보험 검색 필드입니다.")

        rows = self._pool.fetchall(
            f"""
            SELECT
                id,
                customer_id,
                contract_date,
                company,
                policy_number,
                product_name,
                premium,
                insured_person,
                payment_day,
                beneficiary
            FROM insurances
            WHERE deleted_at IS NULL
              AND {allowed[field]} LIKE ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (f"%{keyword.strip()}%", limit, offset),
        )
        return [dict(row) for row in rows]

    def update_insurance(self, insurance_id: int, payload: InsuranceCreate) -> int:
        """Update active insurance and return affected row count."""
        cursor = self._pool.execute(
            """
            UPDATE insurances
            SET
                customer_id = ?,
                contract_date = ?,
                company = ?,
                policy_number = ?,
                product_name = ?,
                premium = ?,
                insured_person = ?,
                payment_day = ?,
                beneficiary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            (
                payload.customer_id,
                payload.contract_date.isoformat(),
                payload.company,
                payload.policy_number,
                payload.product_name,
                str(payload.premium),
                payload.insured_person,
                payload.payment_day,
                payload.beneficiary,
                insurance_id,
            ),
        )
        return cursor.rowcount

    def soft_delete_insurance(self, insurance_id: int) -> int:
        """Soft-delete active insurance and return affected row count."""
        cursor = self._pool.execute(
            """
            UPDATE insurances
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            (insurance_id,),
        )
        return cursor.rowcount
