"""Database schema management."""

from __future__ import annotations

from manim_app.repositories.db_pool import ThreadLocalConnection


def initialize_schema(pool: ThreadLocalConnection) -> None:
    """Create required tables and indexes if they do not exist."""
    pool.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rrn_encrypted BLOB NOT NULL,
            rrn_hash TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            job TEXT,
            payment_card_encrypted BLOB,
            payment_account_encrypted BLOB,
            payout_account_encrypted BLOB,
            medical_history TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
        """
    )

    pool.execute(
        """
        CREATE TABLE IF NOT EXISTS insurances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            contract_date TEXT NOT NULL,
            company TEXT NOT NULL,
            policy_number TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            premium TEXT NOT NULL,
            insured_person TEXT NOT NULL,
            payment_day INTEGER NOT NULL,
            beneficiary TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
        )
        """
    )

    pool.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id INTEGER,
            detail TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    pool.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
    pool.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)")
    pool.execute("CREATE INDEX IF NOT EXISTS idx_insurances_customer ON insurances(customer_id)")
    pool.execute("CREATE INDEX IF NOT EXISTS idx_insurances_policy ON insurances(policy_number)")
    pool.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)")
