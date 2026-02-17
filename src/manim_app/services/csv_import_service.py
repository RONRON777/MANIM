"""CSV import service for customer and insurance records."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from manim_app.models.customer import CustomerCreate
from manim_app.models.insurance import InsuranceCreate
from manim_app.services.customer_service import CustomerService
from manim_app.services.insurance_service import InsuranceService

CUSTOMER_CSV_HEADERS = [
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
]

INSURANCE_CSV_HEADERS = [
    "고객ID",
    "계약일자",
    "보험사",
    "증권번호",
    "상품명",
    "보험료",
    "피보험자",
    "결제일",
    "수익자",
]


@dataclass
class CsvImportResult:
    """Result summary for CSV imports."""

    created_count: int
    failed_count: int
    error_messages: list[str]


class CsvImportService:
    """Imports records from CSV and delegates persistence to services."""

    def __init__(self, customer_service: CustomerService, insurance_service: InsuranceService):
        self._customer_service = customer_service
        self._insurance_service = insurance_service

    @staticmethod
    def _validate_headers(fieldnames: list[str] | None, required: list[str]) -> None:
        if fieldnames is None:
            raise ValueError("CSV 헤더가 없습니다.")
        missing = [header for header in required if header not in fieldnames]
        if missing:
            raise ValueError(f"CSV 헤더 누락: {', '.join(missing)}")

    def import_customers(self, file_path: str) -> CsvImportResult:
        """Import customer CSV and return success/failure counts."""
        created_count = 0
        failed_count = 0
        errors: list[str] = []

        with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_headers(reader.fieldnames, CUSTOMER_CSV_HEADERS)

            for row_index, row in enumerate(reader, start=2):
                try:
                    payload = CustomerCreate(
                        name=row["이름"],
                        rrn=row["주민번호"],
                        phone=row["연락처"],
                        address=row["주소"],
                        job=row["직업"],
                        payment_card=row["카드번호"],
                        payment_account=row["결제계좌"],
                        payout_account=row["보험금수령계좌"],
                        medical_history=row["병력"],
                        note=row["비고"],
                    )
                    self._customer_service.create_customer(payload)
                    created_count += 1
                except (ValueError, KeyError, TypeError) as error:
                    failed_count += 1
                    if len(errors) < 10:
                        errors.append(f"{row_index}행: {error}")

        return CsvImportResult(
            created_count=created_count,
            failed_count=failed_count,
            error_messages=errors,
        )

    def import_insurances(self, file_path: str) -> CsvImportResult:
        """Import insurance CSV and return success/failure counts."""
        created_count = 0
        failed_count = 0
        errors: list[str] = []

        with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_headers(reader.fieldnames, INSURANCE_CSV_HEADERS)

            for row_index, row in enumerate(reader, start=2):
                try:
                    payload = InsuranceCreate(
                        customer_id=int(row["고객ID"]),
                        contract_date=datetime.strptime(row["계약일자"], "%Y-%m-%d").date(),
                        company=row["보험사"],
                        policy_number=row["증권번호"],
                        product_name=row["상품명"],
                        premium=Decimal(row["보험료"]),
                        insured_person=row["피보험자"],
                        payment_day=int(row["결제일"]),
                        beneficiary=row["수익자"],
                    )
                    self._insurance_service.create_insurance(payload)
                    created_count += 1
                except (InvalidOperation, ValueError, KeyError, TypeError) as error:
                    failed_count += 1
                    if len(errors) < 10:
                        errors.append(f"{row_index}행: {error}")

        return CsvImportResult(
            created_count=created_count,
            failed_count=failed_count,
            error_messages=errors,
        )
