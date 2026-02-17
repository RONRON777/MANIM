"""Customer service with validation, masking, and audit logs."""

from __future__ import annotations

from manim_app.core.crypto import mask_account, mask_rrn
from manim_app.core.validation import validate_phone, validate_rrn
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
            name=payload.name.strip(),
            rrn=validate_rrn(payload.rrn),
            phone=validate_phone(payload.phone.strip()),
            address=payload.address.strip(),
            job=payload.job.strip(),
            payment_card=payload.payment_card.strip(),
            payment_account=payload.payment_account.strip(),
            payout_account=payload.payout_account.strip(),
            medical_history=payload.medical_history.strip(),
            note=payload.note.strip(),
        )

    def create_customer(self, payload: CustomerCreate) -> int:
        """Validate, persist, and audit customer creation."""
        normalized = self._validate(payload)
        customer_id = self._customer_repo.create_customer(normalized)
        self._audit_repo.add_log("CREATE", "customer", customer_id, "customer created")
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
        self._audit_repo.add_log("READ", "customer", None, f"customer list limit={limit} offset={offset}")
        return customers

    def update_customer(self, customer_id: int, payload: CustomerCreate) -> None:
        """Update customer and write audit log."""
        normalized = self._validate(payload)
        updated = self._customer_repo.update_customer(customer_id, normalized)
        if updated == 0:
            raise ValueError("수정할 고객 정보를 찾을 수 없습니다.")
        self._audit_repo.add_log("UPDATE", "customer", customer_id, "customer updated")

    def delete_customer(self, customer_id: int) -> None:
        """Soft-delete customer and write audit log."""
        deleted = self._customer_repo.soft_delete_customer(customer_id)
        if deleted == 0:
            raise ValueError("삭제할 고객 정보를 찾을 수 없습니다.")
        self._audit_repo.add_log("DELETE", "customer", customer_id, "customer soft-deleted")
