"""Application dependency container."""

from __future__ import annotations

from dataclasses import dataclass

from manim_app.core.config import AppConfig, ensure_runtime_keys, get_required_env, load_config
from manim_app.core.crypto import CryptoService
from manim_app.repositories.audit_repository import AuditRepository
from manim_app.repositories.customer_repository import CustomerRepository
from manim_app.repositories.db_pool import ThreadLocalConnection
from manim_app.repositories.insurance_repository import InsuranceRepository
from manim_app.repositories.schema import initialize_schema
from manim_app.services.csv_import_service import CsvImportService
from manim_app.services.customer_service import CustomerService
from manim_app.services.insurance_service import InsuranceService


@dataclass
class ServiceContainer:
    """Wires repositories and services."""

    config: AppConfig
    customer_service: CustomerService
    insurance_service: InsuranceService
    csv_import_service: CsvImportService
    audit_repo: AuditRepository


def build_container() -> ServiceContainer:
    """Build dependencies and initialize schema."""
    config = load_config()
    ensure_runtime_keys(config.database.path)
    encryption_key = get_required_env(config.encryption.key_env)
    crypto = CryptoService.from_base64_key(encryption_key)

    pool = ThreadLocalConnection(config)
    initialize_schema(pool)

    audit_repo = AuditRepository(pool)
    customer_repo = CustomerRepository(pool, crypto)
    insurance_repo = InsuranceRepository(pool)

    customer_service = CustomerService(customer_repo, audit_repo)
    insurance_service = InsuranceService(insurance_repo, customer_repo, audit_repo)

    return ServiceContainer(
        config=config,
        customer_service=customer_service,
        insurance_service=insurance_service,
        csv_import_service=CsvImportService(customer_service, insurance_service),
        audit_repo=audit_repo,
    )
