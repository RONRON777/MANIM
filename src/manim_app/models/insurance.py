"""Insurance domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class InsuranceCreate:
    """Input model for insurance data."""

    customer_id: int
    contract_date: date
    company: str
    policy_number: str
    product_name: str
    premium: Decimal
    insured_person: str
    payment_day: int
    beneficiary: str


@dataclass
class InsuranceView:
    """Output model for insurance retrieval."""

    id: int
    customer_id: int
    contract_date: str
    company: str
    policy_number: str
    product_name: str
    premium: str
    insured_person: str
    payment_day: int
    beneficiary: str
