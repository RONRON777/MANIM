"""Tests for CSV import service."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

from manim_app.services.csv_import_service import CsvImportService


class FakeCustomerService:
    def __init__(self):
        self.items = []

    def create_customer(self, payload):
        self.items.append(payload)
        return len(self.items)


class FakeInsuranceService:
    def __init__(self):
        self.items = []

    def create_insurance(self, payload):
        assert payload.contract_date <= date.today()
        assert payload.premium >= Decimal("0")
        self.items.append(payload)
        return len(self.items)


def test_import_customers(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "이름",
            "주민번호",
            "연락처",
            "주소",
            "직업",
            "카드번호",
            "결제계좌",
            "보험금수령계좌",
            "병력",
            "비고",
        ])
        writer.writerow([
            "홍길동",
            "971013-9019902",
            "010-1234-5678",
            "서울",
            "개발자",
            "1234123412341234",
            "12345678901234",
            "33334444555566",
            "없음",
            "메모",
        ])

    service = CsvImportService(FakeCustomerService(), FakeInsuranceService())
    result = service.import_customers(str(csv_path))

    assert result.created_count == 1
    assert result.failed_count == 0


def test_import_insurances(tmp_path) -> None:
    csv_path = tmp_path / "insurances.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "고객ID",
            "계약일자",
            "보험사",
            "증권번호",
            "상품명",
            "보험료",
            "피보험자",
            "결제일",
            "수익자",
        ])
        writer.writerow([
            "1",
            "2024-01-01",
            "테스트보험",
            "POL-100",
            "암보험",
            "50000",
            "홍길동",
            "25",
            "홍길순",
        ])

    service = CsvImportService(FakeCustomerService(), FakeInsuranceService())
    result = service.import_insurances(str(csv_path))

    assert result.created_count == 1
    assert result.failed_count == 0
