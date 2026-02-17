"""Customer service with validation, masking, and audit logs."""

from __future__ import annotations

import json

from manim_app.core.crypto import mask_account, mask_rrn
from manim_app.core.validation import (
    validate_optional_number,
    validate_phone,
    validate_required_text,
    validate_rrn,
)
from manim_app.models.customer import CustomerCreate, CustomerView
from manim_app.repositories.audit_repository import AuditRepository
from manim_app.repositories.customer_repository import CustomerRepository


class CustomerService:
    """Coordinates customer use cases."""

    def __init__(self, customer_repo: CustomerRepository, audit_repo: AuditRepository):
        self._customer_repo = customer_repo
        self._audit_repo = audit_repo

    @staticmethod
    def _validate(payload: CustomerCreate) -> CustomerCreate:
        return CustomerCreate(
            name=validate_required_text(payload.name, "이름"),
            rrn=validate_rrn(payload.rrn),
            phone=validate_phone(payload.phone.strip()),
            address=validate_required_text(payload.address, "주소"),
            job=payload.job.strip(),
            payment_card=validate_optional_number(
                payload.payment_card,
                "카드번호",
                min_length=12,
                max_length=19,
            ),
            payment_account=validate_optional_number(
                payload.payment_account,
                "결제 계좌",
                min_length=8,
                max_length=20,
            ),
            payout_account=validate_optional_number(
                payload.payout_account,
                "보험금 수령 계좌",
                min_length=8,
                max_length=20,
            ),
            medical_history=payload.medical_history.strip(),
            note=payload.note.strip(),
        )

    def next_customer_id(self) -> int:
        """Return the next customer id for UI defaults."""
        return self._customer_repo.next_customer_id()

    def create_customer(self, payload: CustomerCreate) -> int:
        """Validate, persist, and audit customer creation."""
        normalized = self._validate(payload)
        customer_id = self._customer_repo.create_customer(normalized)
        after = self._snapshot(customer_id)
        self._audit_repo.add_log(
            "CREATE",
            "customer",
            customer_id,
            json.dumps({"event": "customer created", "after": after}, ensure_ascii=False),
        )
        return customer_id

    def get_customer(self, customer_id: int, reveal_sensitive: bool = False) -> CustomerView:
        """Fetch one customer with masked or decrypted sensitive fields."""
        row = self._customer_repo.get_customer(customer_id)
        if not row:
            raise ValueError("고객 정보를 찾을 수 없습니다.")

        rrn = self._customer_repo.decrypt_rrn(row["rrn_encrypted"])
        card = self._customer_repo.decrypt_account(row["payment_card_encrypted"])
        account = self._customer_repo.decrypt_account(row["payment_account_encrypted"])
        payout = self._customer_repo.decrypt_account(row["payout_account_encrypted"])

        self._audit_repo.add_log("READ", "customer", customer_id, "customer read")

        if not reveal_sensitive:
            rrn = mask_rrn(rrn)
            card = mask_account(card)
            account = mask_account(account)
            payout = mask_account(payout)

        return CustomerView(
            id=row["id"],
            name=row["name"],
            rrn=rrn,
            phone=row["phone"],
            address=row["address"],
            job=row["job"],
            payment_card=card,
            payment_account=account,
            payout_account=payout,
            medical_history=row["medical_history"],
            note=row["note"],
        )

    def list_customers(self, limit: int = 50, offset: int = 0) -> list[CustomerView]:
        """List customers with masked sensitive fields for safe UI display."""
        rows = self._customer_repo.list_customers(limit=limit, offset=offset)
        customers: list[CustomerView] = []
        for row in rows:
            rrn = self._customer_repo.decrypt_rrn(row["rrn_encrypted"])
            card = self._customer_repo.decrypt_account(row["payment_card_encrypted"])
            account = self._customer_repo.decrypt_account(row["payment_account_encrypted"])
            payout = self._customer_repo.decrypt_account(row["payout_account_encrypted"])
            customers.append(
                CustomerView(
                    id=row["id"],
                    name=row["name"],
                    rrn=mask_rrn(rrn),
                    phone=row["phone"],
                    address=row["address"],
                    job=row["job"],
                    payment_card=mask_account(card),
                    payment_account=mask_account(account),
                    payout_account=mask_account(payout),
                    medical_history=row["medical_history"],
                    note=row["note"],
                )
            )
        self._audit_repo.add_log(
            "READ",
            "customer",
            None,
            f"customer list limit={limit} offset={offset}",
        )
        return customers

    def search_customers(
        self,
        field: str,
        keyword: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CustomerView]:
        """Search customers by selected field."""
        rows = self._customer_repo.search_customers(
            field=field,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        customers: list[CustomerView] = []
        for row in rows:
            rrn = self._customer_repo.decrypt_rrn(row["rrn_encrypted"])
            card = self._customer_repo.decrypt_account(row["payment_card_encrypted"])
            account = self._customer_repo.decrypt_account(row["payment_account_encrypted"])
            payout = self._customer_repo.decrypt_account(row["payout_account_encrypted"])
            customers.append(
                CustomerView(
                    id=row["id"],
                    name=row["name"],
                    rrn=mask_rrn(rrn),
                    phone=row["phone"],
                    address=row["address"],
                    job=row["job"],
                    payment_card=mask_account(card),
                    payment_account=mask_account(account),
                    payout_account=mask_account(payout),
                    medical_history=row["medical_history"],
                    note=row["note"],
                )
            )
        self._audit_repo.add_log(
            "READ",
            "customer",
            None,
            f"customer search field={field} keyword={keyword}",
        )
        return customers

    def update_customer(self, customer_id: int, payload: CustomerCreate) -> None:
        """Update customer and write audit log."""
        before = self._snapshot(customer_id)
        normalized = self._validate(payload)
        updated = self._customer_repo.update_customer(customer_id, normalized)
        if updated == 0:
            raise ValueError("수정할 고객 정보를 찾을 수 없습니다.")
        after = self._snapshot(customer_id)
        self._audit_repo.add_log(
            "UPDATE",
            "customer",
            customer_id,
            json.dumps(
                {
                    "event": "customer updated",
                    "changes": self._diff(before, after),
                },
                ensure_ascii=False,
            ),
        )

    def delete_customer(self, customer_id: int) -> None:
        """Soft-delete customer and write audit log."""
        before = self._snapshot(customer_id)
        deleted = self._customer_repo.soft_delete_customer(customer_id)
        if deleted == 0:
            raise ValueError("삭제할 고객 정보를 찾을 수 없습니다.")
        self._audit_repo.add_log(
            "DELETE",
            "customer",
            customer_id,
            json.dumps({"event": "customer soft-deleted", "before": before}, ensure_ascii=False),
        )

    def restore_customer(self, customer_id: int) -> None:
        """Restore a soft-deleted customer and write audit log."""
        restored = self._customer_repo.restore_customer(customer_id)
        if restored == 0:
            raise ValueError("복구할 고객 정보를 찾을 수 없습니다.")
        after = self._snapshot(customer_id)
        self._audit_repo.add_log(
            "UPDATE",
            "customer",
            customer_id,
            json.dumps({"event": "customer restored", "after": after}, ensure_ascii=False),
        )

    def hard_delete_customer(self, customer_id: int) -> None:
        """Hard-delete customer and related records."""
        deleted = self._customer_repo.hard_delete_customer(customer_id)
        if deleted == 0:
            raise ValueError("영구 삭제할 고객 정보를 찾을 수 없습니다.")
        self._audit_repo.add_log("DELETE", "customer", customer_id, "customer hard-deleted")

    def purge_all_customers(self) -> None:
        """Delete all customer and insurance rows."""
        self._customer_repo.purge_all_customers()
        self._audit_repo.add_log("DELETE", "customer", None, "all customers purged")

    def _snapshot(self, customer_id: int) -> dict[str, str]:
        """Build a masked snapshot for audit logs."""
        row = self._customer_repo.get_customer(customer_id)
        if not row:
            return {}
        rrn = self._customer_repo.decrypt_rrn(row["rrn_encrypted"])
        card = self._customer_repo.decrypt_account(row["payment_card_encrypted"])
        account = self._customer_repo.decrypt_account(row["payment_account_encrypted"])
        payout = self._customer_repo.decrypt_account(row["payout_account_encrypted"])
        return {
            "name": row["name"] or "",
            "rrn": mask_rrn(rrn),
            "phone": row["phone"] or "",
            "address": row["address"] or "",
            "job": row["job"] or "",
            "payment_card": mask_account(card),
            "payment_account": mask_account(account),
            "payout_account": mask_account(payout),
            "medical_history": row["medical_history"] or "",
            "note": row["note"] or "",
        }

    @staticmethod
    def _diff(before: dict[str, str], after: dict[str, str]) -> dict[str, dict[str, str]]:
        """Return changed fields for audit logs."""
        changes: dict[str, dict[str, str]] = {}
        for key in sorted(set(before) | set(after)):
            old = before.get(key, "")
            new = after.get(key, "")
            if old != new:
                changes[key] = {"before": old, "after": new}
        return changes
