"""Tests for validation rules."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from manim_app.core.validation import (
    validate_contract_date,
    validate_optional_number,
    validate_payment_day,
    validate_phone,
    validate_premium,
    validate_required_text,
    validate_rrn,
)


def test_validate_rrn_checksum_valid() -> None:
    assert validate_rrn("971013-9019902") == "9710139019902"


def test_validate_phone_pattern() -> None:
    assert validate_phone("010-1234-5678") == "010-1234-5678"


def test_validate_premium_positive() -> None:
    assert validate_premium(Decimal("10000")) == Decimal("10000")


def test_validate_contract_date_reject_future() -> None:
    with pytest.raises(ValueError):
        validate_contract_date(date.today() + timedelta(days=1))


def test_validate_payment_day_range() -> None:
    assert validate_payment_day(15) == 15
    with pytest.raises(ValueError):
        validate_payment_day(0)


def test_validate_required_text() -> None:
    assert validate_required_text(" 보험사 ", "보험사") == "보험사"
    with pytest.raises(ValueError):
        validate_required_text("   ", "보험사")


def test_validate_optional_number_empty_or_digits() -> None:
    assert validate_optional_number("", "결제 계좌", 8, 20) == ""
    assert validate_optional_number("1234-5678-9012", "카드번호", 12, 19) == "123456789012"
    with pytest.raises(ValueError):
        validate_optional_number("abcd", "카드번호", 12, 19)
