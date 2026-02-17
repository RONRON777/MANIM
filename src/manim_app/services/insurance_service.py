"""Insurance service."""

from __future__ import annotations

from manim_app.core.validation import validate_contract_date, validate_payment_day, validate_premium
from manim_app.models.insurance import InsuranceCreate, InsuranceView
from manim_app.repositories.audit_repository import AuditRepository
from manim_app.repositories.customer_repository import CustomerRepository
from manim_app.repositories.insurance_repository import InsuranceRepository


class InsuranceService:
    """Coordinates insurance use cases."""

    def __init__(
        self,
        insurance_repo: InsuranceRepository,
        customer_repo: CustomerRepository,
        audit_repo: AuditRepository,
    ):
        self._insurance_repo = insurance_repo
        self._customer_repo = customer_repo
        self._audit_repo = audit_repo

    def _validate(self, payload: InsuranceCreate) -> InsuranceCreate:
        if not self._customer_repo.exists_active_customer(payload.customer_id):
            raise ValueError("유효한 고객(계약자) ID가 아닙니다.")

        return InsuranceCreate(
            customer_id=payload.customer_id,
            contract_date=validate_contract_date(payload.contract_date),
            company=payload.company.strip(),
            policy_number=payload.policy_number.strip(),
            product_name=payload.product_name.strip(),
            premium=validate_premium(payload.premium),
            insured_person=payload.insured_person.strip(),
            payment_day=validate_payment_day(int(payload.payment_day)),
            beneficiary=payload.beneficiary.strip(),
        )

    @staticmethod
    def _to_view(row: dict) -> InsuranceView:
        return InsuranceView(
            id=row["id"],
            customer_id=row["customer_id"],
            contract_date=row["contract_date"],
            company=row["company"],
            policy_number=row["policy_number"],
            product_name=row["product_name"],
            premium=row["premium"],
            insured_person=row["insured_person"],
            payment_day=row["payment_day"],
            beneficiary=row["beneficiary"],
        )

    def create_insurance(self, payload: InsuranceCreate) -> int:
        """Validate, persist, and audit insurance creation."""
        validated = self._validate(payload)
        insurance_id = self._insurance_repo.create_insurance(validated)
        self._audit_repo.add_log("CREATE", "insurance", insurance_id, "insurance created")
        return insurance_id

    def get_insurance(self, insurance_id: int) -> InsuranceView:
        """Fetch one insurance by id."""
        row = self._insurance_repo.get_insurance(insurance_id)
        if not row:
            raise ValueError("보험 정보를 찾을 수 없습니다.")
        self._audit_repo.add_log("READ", "insurance", insurance_id, "insurance read")
        return self._to_view(row)

    def list_insurances(self, customer_id: int, limit: int = 50, offset: int = 0) -> list[InsuranceView]:
        """List insurances for one customer."""
        if not self._customer_repo.exists_active_customer(customer_id):
            raise ValueError("유효한 고객(계약자) ID가 아닙니다.")

        rows = self._insurance_repo.list_insurances(customer_id=customer_id, limit=limit, offset=offset)
        self._audit_repo.add_log(
            "READ",
            "insurance",
            None,
            f"insurance list customer_id={customer_id} limit={limit} offset={offset}",
        )
        return [self._to_view(row) for row in rows]

    def update_insurance(self, insurance_id: int, payload: InsuranceCreate) -> None:
        """Update one insurance and write audit log."""
        validated = self._validate(payload)
        updated = self._insurance_repo.update_insurance(insurance_id, validated)
        if updated == 0:
            raise ValueError("수정할 보험 정보를 찾을 수 없습니다.")
        self._audit_repo.add_log("UPDATE", "insurance", insurance_id, "insurance updated")

    def delete_insurance(self, insurance_id: int) -> None:
        """Soft-delete one insurance and write audit log."""
        deleted = self._insurance_repo.soft_delete_insurance(insurance_id)
        if deleted == 0:
            raise ValueError("삭제할 보험 정보를 찾을 수 없습니다.")
        self._audit_repo.add_log("DELETE", "insurance", insurance_id, "insurance soft-deleted")
