"""Customer repository with encrypted sensitive fields."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from manim_app.core.crypto import CryptoService
from manim_app.models.customer import CustomerCreate
from manim_app.repositories.db_pool import ThreadLocalConnection


class CustomerRepository:
    """Handles customer persistence and retrieval."""

    def __init__(self, pool: ThreadLocalConnection, crypto_service: CryptoService):
        self._pool = pool
        self._crypto = crypto_service

    @staticmethod
    def _hash_rrn(rrn: str) -> str:
        return hashlib.sha256(rrn.encode("utf-8")).hexdigest()

    def create_customer(self, payload: CustomerCreate) -> int:
        """Insert customer with encrypted sensitive fields and return new id."""
        rrn_hash = self._hash_rrn(payload.rrn)
        try:
            cursor = self._pool.execute(
                """
                INSERT INTO customers (
                    name,
                    rrn_encrypted,
                    rrn_hash,
                    phone,
                    address,
                    job,
                    payment_card_encrypted,
                    payment_account_encrypted,
                    payout_account_encrypted,
                    medical_history,
                    note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.name,
                    self._crypto.encrypt_text(payload.rrn),
                    rrn_hash,
                    payload.phone,
                    payload.address,
                    payload.job,
                    self._crypto.encrypt_text(payload.payment_card),
                    self._crypto.encrypt_text(payload.payment_account),
                    self._crypto.encrypt_text(payload.payout_account),
                    payload.medical_history,
                    payload.note,
                ),
            )
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            if "customers.rrn_hash" not in str(error):
                raise

            active_row = self._pool.fetchone(
                """
                SELECT id
                FROM customers
                WHERE rrn_hash = ? AND deleted_at IS NULL
                LIMIT 1
                """,
                (rrn_hash,),
            )
            if active_row:
                raise ValueError("이미 등록된 주민번호입니다.") from error

            deleted_row = self._pool.fetchone(
                """
                SELECT id
                FROM customers
                WHERE rrn_hash = ? AND deleted_at IS NOT NULL
                LIMIT 1
                """,
                (rrn_hash,),
            )
            if deleted_row:
                self._pool.execute(
                    """
                    UPDATE customers
                    SET rrn_hash = rrn_hash || ':deleted:' || id
                    WHERE id = ?
                    """,
                    (deleted_row["id"],),
                )
                cursor = self._pool.execute(
                    """
                    INSERT INTO customers (
                        name,
                        rrn_encrypted,
                        rrn_hash,
                        phone,
                        address,
                        job,
                        payment_card_encrypted,
                        payment_account_encrypted,
                        payout_account_encrypted,
                        medical_history,
                        note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.name,
                        self._crypto.encrypt_text(payload.rrn),
                        rrn_hash,
                        payload.phone,
                        payload.address,
                        payload.job,
                        self._crypto.encrypt_text(payload.payment_card),
                        self._crypto.encrypt_text(payload.payment_account),
                        self._crypto.encrypt_text(payload.payout_account),
                        payload.medical_history,
                        payload.note,
                    ),
                )
                return int(cursor.lastrowid)

            raise ValueError("주민번호 중복이 감지되었습니다.") from error

    def decrypt_rrn(self, encrypted_rrn: bytes) -> str:
        """Decrypt stored RRN bytes."""
        return self._crypto.decrypt_text(encrypted_rrn)

    def decrypt_account(self, encrypted_value: bytes) -> str:
        """Decrypt stored account/card bytes."""
        return self._crypto.decrypt_text(encrypted_value)

    def next_customer_id(self) -> int:
        """Return the next customer id in insertion order."""
        row = self._pool.fetchone("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM customers")
        return int(row["next_id"]) if row else 1

    def exists_active_customer(self, customer_id: int) -> bool:
        """Return True when active customer exists."""
        row = self._pool.fetchone(
            """
            SELECT 1
            FROM customers
            WHERE id = ? AND deleted_at IS NULL
            LIMIT 1
            """,
            (customer_id,),
        )
        return row is not None

    def get_customer(self, customer_id: int) -> dict[str, Any] | None:
        """Fetch single active customer row."""
        row = self._pool.fetchone(
            """
            SELECT
                id,
                name,
                rrn_encrypted,
                phone,
                address,
                job,
                payment_card_encrypted,
                payment_account_encrypted,
                payout_account_encrypted,
                medical_history,
                note
            FROM customers
            WHERE id = ? AND deleted_at IS NULL
            """,
            (customer_id,),
        )
        return dict(row) if row else None

    def list_customers(self, limit: int, offset: int) -> list[dict[str, Any]]:
        """Fetch active customers with pagination."""
        rows = self._pool.fetchall(
            """
            SELECT
                id,
                name,
                rrn_encrypted,
                phone,
                address,
                job,
                payment_card_encrypted,
                payment_account_encrypted,
                payout_account_encrypted,
                medical_history,
                note
            FROM customers
            WHERE deleted_at IS NULL
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [dict(row) for row in rows]

    def search_customers(
        self,
        field: str,
        keyword: str,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """Search active customers by a permitted text field."""
        allowed = {
            "id": "CAST(id AS TEXT)",
            "name": "name",
            "phone": "phone",
            "address": "address",
            "job": "job",
        }
        if field not in allowed:
            raise ValueError("지원하지 않는 고객 검색 필드입니다.")

        rows = self._pool.fetchall(
            f"""
            SELECT
                id,
                name,
                rrn_encrypted,
                phone,
                address,
                job,
                payment_card_encrypted,
                payment_account_encrypted,
                payout_account_encrypted,
                medical_history,
                note
            FROM customers
            WHERE deleted_at IS NULL
              AND {allowed[field]} LIKE ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (f"%{keyword.strip()}%", limit, offset),
        )
        return [dict(row) for row in rows]

    def update_customer(self, customer_id: int, payload: CustomerCreate) -> int:
        """Update active customer and return affected row count."""
        try:
            cursor = self._pool.execute(
                """
                UPDATE customers
                SET
                    name = ?,
                    rrn_encrypted = ?,
                    rrn_hash = ?,
                    phone = ?,
                    address = ?,
                    job = ?,
                    payment_card_encrypted = ?,
                    payment_account_encrypted = ?,
                    payout_account_encrypted = ?,
                    medical_history = ?,
                    note = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND deleted_at IS NULL
                """,
                (
                    payload.name,
                    self._crypto.encrypt_text(payload.rrn),
                    self._hash_rrn(payload.rrn),
                    payload.phone,
                    payload.address,
                    payload.job,
                    self._crypto.encrypt_text(payload.payment_card),
                    self._crypto.encrypt_text(payload.payment_account),
                    self._crypto.encrypt_text(payload.payout_account),
                    payload.medical_history,
                    payload.note,
                    customer_id,
                ),
            )
            return cursor.rowcount
        except sqlite3.IntegrityError as error:
            if "customers.rrn_hash" in str(error):
                raise ValueError("이미 등록된 주민번호입니다.") from error
            raise

    def soft_delete_customer(self, customer_id: int) -> int:
        """Soft-delete customer if they do not have active insurances."""
        insurance_row = self._pool.fetchone(
            """
            SELECT 1
            FROM insurances
            WHERE customer_id = ? AND deleted_at IS NULL
            LIMIT 1
            """,
            (customer_id,),
        )
        if insurance_row:
            raise ValueError("활성 보험이 있는 고객은 삭제할 수 없습니다.")

        cursor = self._pool.execute(
            """
            UPDATE customers
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                rrn_hash = rrn_hash || ':deleted:' || id
            WHERE id = ? AND deleted_at IS NULL
            """,
            (customer_id,),
        )
        return cursor.rowcount

    def restore_customer(self, customer_id: int) -> int:
        """Restore a soft-deleted customer when no active RRN conflict exists."""
        row = self._pool.fetchone(
            """
            SELECT id, rrn_encrypted, deleted_at
            FROM customers
            WHERE id = ?
            LIMIT 1
            """,
            (customer_id,),
        )
        if not row:
            return 0
        if row["deleted_at"] is None:
            return 0

        rrn = self._crypto.decrypt_text(row["rrn_encrypted"])
        rrn_hash = self._hash_rrn(rrn)

        conflict = self._pool.fetchone(
            """
            SELECT id
            FROM customers
            WHERE rrn_hash = ? AND deleted_at IS NULL AND id != ?
            LIMIT 1
            """,
            (rrn_hash, customer_id),
        )
        if conflict:
            raise ValueError(
                "동일 주민번호의 활성 고객이 있어 복구할 수 없습니다."
            )

        cursor = self._pool.execute(
            """
            UPDATE customers
            SET deleted_at = NULL,
                updated_at = CURRENT_TIMESTAMP,
                rrn_hash = ?
            WHERE id = ? AND deleted_at IS NOT NULL
            """,
            (rrn_hash, customer_id),
        )
        return cursor.rowcount

    def hard_delete_customer(self, customer_id: int) -> int:
        """Hard-delete customer and all related insurances."""
        self._pool.execute(
            """
            DELETE FROM insurances
            WHERE customer_id = ?
            """,
            (customer_id,),
        )
        cursor = self._pool.execute(
            """
            DELETE FROM customers
            WHERE id = ?
            """,
            (customer_id,),
        )
        return cursor.rowcount

    def purge_all_customers(self) -> None:
        """Delete all customers and related insurances, reset sequences."""
        self._pool.execute("DELETE FROM insurances")
        self._pool.execute("DELETE FROM customers")
        self._pool.execute("DELETE FROM sqlite_sequence WHERE name = 'insurances'")
        self._pool.execute("DELETE FROM sqlite_sequence WHERE name = 'customers'")
