"""Customer domain models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CustomerCreate:
    """Input model for creating a customer(contractor)."""

    name: str
    rrn: str
    phone: str
    address: str
    job: str
    payment_card: str
    payment_account: str
    payout_account: str
    medical_history: str
    note: str


@dataclass
class CustomerView:
    """Output model for customer retrieval."""

    id: int
    name: str
    rrn: str
    phone: str
    address: str
    job: str
    payment_card: str
    payment_account: str
    payout_account: str
    medical_history: str
    note: str
