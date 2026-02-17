"""Input validation rules for customer and insurance records."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

PHONE_PATTERN = re.compile(r"^010-\d{4}-\d{4}$")


def validate_rrn(rrn: str) -> str:
    """Validate Korean RRN using 13-digit checksum and return normalized value."""
    digits = rrn.replace("-", "")
    if not digits.isdigit() or len(digits) != 13:
        raise ValueError("주민번호는 13자리 숫자여야 합니다.")

    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    total = sum(int(digits[i]) * weights[i] for i in range(12))
    check = (11 - (total % 11)) % 10
    if check != int(digits[-1]):
        raise ValueError("주민번호 체크섬이 유효하지 않습니다.")

    return digits


def validate_phone(phone: str) -> str:
    """Validate mobile number format: 010-####-####."""
    if not PHONE_PATTERN.match(phone):
        raise ValueError("연락처 형식은 010-1234-5678 이어야 합니다.")
    return phone


def validate_premium(premium: Decimal) -> Decimal:
    """Validate premium value range."""
    if premium <= 0:
        raise ValueError("보험료는 양수여야 합니다.")
    if premium > Decimal("1000000000"):
        raise ValueError("보험료 상한(1,000,000,000)을 초과했습니다.")
    return premium


def validate_contract_date(contract_date: date) -> date:
    """Disallow future contract dates."""
    if contract_date > date.today():
        raise ValueError("계약일자는 미래 날짜를 허용하지 않습니다.")
    return contract_date


def validate_payment_day(payment_day: int) -> int:
    """Validate monthly payment day range."""
    if payment_day < 1 or payment_day > 31:
        raise ValueError("결제일은 1~31 사이여야 합니다.")
    return payment_day
