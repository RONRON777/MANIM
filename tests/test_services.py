"""Integration-like tests for customer and insurance services."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from manim_app.core.config import AppConfig, DatabaseConfig, EncryptionConfig, LoggingConfig
from manim_app.core.crypto import CryptoService
from manim_app.models.customer import CustomerCreate
from manim_app.models.insurance import InsuranceCreate
from manim_app.repositories.audit_repository import AuditRepository
from manim_app.repositories.customer_repository import CustomerRepository
from manim_app.repositories.db_pool import ThreadLocalConnection
from manim_app.repositories.insurance_repository import InsuranceRepository
from manim_app.repositories.schema import initialize_schema
from manim_app.services.customer_service import CustomerService
from manim_app.services.insurance_service import InsuranceService


def build_services(tmp_path):
    config = AppConfig(
        database=DatabaseConfig(
            path=str(tmp_path / "test.db"),
            key_env="MANIM_DB_KEY",
            allow_sqlite_fallback=True,
        ),
        encryption=EncryptionConfig(key_env="MANIM_ENCRYPTION_KEY"),
        logging=LoggingConfig(retention_days=1095),
    )
    pool = ThreadLocalConnection(config)
    initialize_schema(pool)

    crypto = CryptoService.from_base64_key(CryptoService.generate_base64_key())
    audit_repo = AuditRepository(pool)
    customer_repo = CustomerRepository(pool, crypto)
    insurance_repo = InsuranceRepository(pool)

    customer_service = CustomerService(customer_repo, audit_repo)
    insurance_service = InsuranceService(insurance_repo, customer_repo, audit_repo)
    return customer_service, insurance_service


def test_customer_and_insurance_crud(tmp_path) -> None:
    customer_service, insurance_service = build_services(tmp_path)

    customer_id = customer_service.create_customer(
        CustomerCreate(
            name="홍길동",
            rrn="971013-9019902",
            phone="010-1234-5678",
            address="서울",
            job="개발자",
            payment_card="1234123412341234",
            payment_account="12345678901234",
            payout_account="33334444555566",
            medical_history="없음",
            note="테스트",
        )
    )
    listed = customer_service.list_customers(limit=10, offset=0)
    assert listed[0].id == customer_id
    assert listed[0].rrn.endswith("******")

    insurance_id = insurance_service.create_insurance(
        InsuranceCreate(
            customer_id=customer_id,
            contract_date=date.today(),
            company="테스트보험",
            policy_number="POL-001",
            product_name="종합보험",
            premium=Decimal("100000"),
            insured_person="홍길동",
            payment_day=25,
            beneficiary="홍길순",
        )
    )
    insurance = insurance_service.get_insurance(insurance_id)
    assert insurance.policy_number == "POL-001"

    insurance_service.delete_insurance(insurance_id)
    customer_service.delete_customer(customer_id)


def test_customer_optional_payment_fields_can_be_empty(tmp_path) -> None:
    customer_service, _ = build_services(tmp_path)

    customer_id = customer_service.create_customer(
        CustomerCreate(
            name="김철수",
            rrn="971013-9019902",
            phone="010-2222-3333",
            address="부산",
            job="디자이너",
            payment_card="",
            payment_account="",
            payout_account="",
            medical_history="없음",
            note="빈 결제정보 허용",
        )
    )

    customer = customer_service.get_customer(customer_id, reveal_sensitive=True)
    assert customer.payment_card == ""
    assert customer.payment_account == ""
    assert customer.payout_account == ""
