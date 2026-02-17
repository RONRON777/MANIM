"""Main GUI window for customer and insurance management."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from manim_app.models.customer import CustomerCreate
from manim_app.models.insurance import InsuranceCreate
from manim_app.services.csv_import_service import CsvImportService
from manim_app.services.customer_service import CustomerService
from manim_app.services.insurance_service import InsuranceService


class LoadSignals(QObject):
    """Signals for background loading."""

    done = Signal(list)
    error = Signal(str)


class LoadCustomersTask(QRunnable):
    """Background task for loading customer list."""

    def __init__(self, customer_service: CustomerService, limit: int, offset: int):
        super().__init__()
        self.customer_service = customer_service
        self.limit = limit
        self.offset = offset
        self.signals = LoadSignals()

    def run(self) -> None:
        try:
            customers = self.customer_service.list_customers(limit=self.limit, offset=self.offset)
            self.signals.done.emit(customers)
        except Exception as error:  # pylint: disable=broad-except
            self.signals.error.emit(str(error))


class LoadInsurancesTask(QRunnable):
    """Background task for loading insurance list."""

    def __init__(self, insurance_service: InsuranceService, customer_id: int, limit: int, offset: int):
        super().__init__()
        self.insurance_service = insurance_service
        self.customer_id = customer_id
        self.limit = limit
        self.offset = offset
        self.signals = LoadSignals()

    def run(self) -> None:
        try:
            insurances = self.insurance_service.list_insurances(
                customer_id=self.customer_id,
                limit=self.limit,
                offset=self.offset,
            )
            self.signals.done.emit(insurances)
        except Exception as error:  # pylint: disable=broad-except
            self.signals.error.emit(str(error))


class ImportSignals(QObject):
    """Signals for background CSV import."""

    done = Signal(int, int, str)
    error = Signal(str)


class ImportCustomersCsvTask(QRunnable):
    """Background task for importing customers from CSV."""

    def __init__(self, csv_import_service: CsvImportService, file_path: str):
        super().__init__()
        self.csv_import_service = csv_import_service
        self.file_path = file_path
        self.signals = ImportSignals()

    def run(self) -> None:
        try:
            result = self.csv_import_service.import_customers(self.file_path)
            self.signals.done.emit(
                result.created_count,
                result.failed_count,
                "\n".join(result.error_messages),
            )
        except Exception as error:  # pylint: disable=broad-except
            self.signals.error.emit(str(error))


class ImportInsurancesCsvTask(QRunnable):
    """Background task for importing insurances from CSV."""

    def __init__(self, csv_import_service: CsvImportService, file_path: str):
        super().__init__()
        self.csv_import_service = csv_import_service
        self.file_path = file_path
        self.signals = ImportSignals()

    def run(self) -> None:
        try:
            result = self.csv_import_service.import_insurances(self.file_path)
            self.signals.done.emit(
                result.created_count,
                result.failed_count,
                "\n".join(result.error_messages),
            )
        except Exception as error:  # pylint: disable=broad-except
            self.signals.error.emit(str(error))


class MainWindow(QMainWindow):
    """GUI for customer and insurance CRUD flow."""

    def __init__(
        self,
        customer_service: CustomerService,
        insurance_service: InsuranceService,
        csv_import_service: CsvImportService,
    ):
        super().__init__()
        self.customer_service = customer_service
        self.insurance_service = insurance_service
        self.csv_import_service = csv_import_service
        self.thread_pool = QThreadPool.globalInstance()

        self.customer_limit = 50
        self.customer_offset = 0
        self.insurance_limit = 50
        self.insurance_offset = 0

        self.setWindowTitle("MANIM - 보험 고객 관리")
        self.resize(1400, 860)

        self._build_customer_inputs()
        self._build_insurance_inputs()
        self._build_layout()

        self.refresh_customers()

    def _build_customer_inputs(self) -> None:
        self.selected_customer_id_input = QLineEdit()
        self.selected_customer_id_input.setPlaceholderText("수정/삭제 대상 고객 ID")

        self.name_input = QLineEdit()
        self.rrn_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()
        self.job_input = QLineEdit()
        self.card_input = QLineEdit()
        self.account_input = QLineEdit()
        self.payout_input = QLineEdit()
        self.medical_input = QLineEdit()
        self.note_input = QLineEdit()

    def _build_insurance_inputs(self) -> None:
        self.selected_insurance_id_input = QLineEdit()
        self.selected_insurance_id_input.setPlaceholderText("수정/삭제 대상 보험 ID")

        self.insurance_customer_id_input = QLineEdit()
        self.insurance_customer_id_input.setPlaceholderText("보험 소속 고객 ID")

        self.contract_date_input = QLineEdit()
        self.contract_date_input.setPlaceholderText("YYYY-MM-DD")

        self.company_input = QLineEdit()
        self.policy_number_input = QLineEdit()
        self.product_name_input = QLineEdit()
        self.premium_input = QLineEdit()
        self.insured_person_input = QLineEdit()
        self.payment_day_input = QLineEdit()
        self.beneficiary_input = QLineEdit()

    def _build_layout(self) -> None:
        customer_form = QFormLayout()
        customer_form.addRow("대상 고객 ID", self.selected_customer_id_input)
        customer_form.addRow("이름", self.name_input)
        customer_form.addRow("주민번호(######-#######)", self.rrn_input)
        customer_form.addRow("연락처(010-####-####)", self.phone_input)
        customer_form.addRow("주소", self.address_input)
        customer_form.addRow("직업", self.job_input)
        customer_form.addRow("카드번호", self.card_input)
        customer_form.addRow("결제 계좌", self.account_input)
        customer_form.addRow("보험금 수령 계좌", self.payout_input)
        customer_form.addRow("병력", self.medical_input)
        customer_form.addRow("비고", self.note_input)

        add_customer_button = QPushButton("고객 추가")
        add_customer_button.clicked.connect(self.create_customer)

        update_customer_button = QPushButton("고객 수정")
        update_customer_button.clicked.connect(self.update_customer)

        delete_customer_button = QPushButton("고객 삭제")
        delete_customer_button.clicked.connect(self.delete_customer)

        load_masked_button = QPushButton("선택 고객 불러오기(마스킹)")
        load_masked_button.clicked.connect(self.load_customer_masked)

        load_unmasked_button = QPushButton("선택 고객 민감정보 보기")
        load_unmasked_button.clicked.connect(self.load_customer_unmasked)

        import_customers_button = QPushButton("고객 CSV 가져오기")
        import_customers_button.clicked.connect(self.import_customers_from_csv)

        refresh_customers_button = QPushButton("고객 목록 새로고침")
        refresh_customers_button.clicked.connect(self.refresh_customers)

        customer_buttons = QHBoxLayout()
        customer_buttons.addWidget(add_customer_button)
        customer_buttons.addWidget(update_customer_button)
        customer_buttons.addWidget(delete_customer_button)
        customer_buttons.addWidget(load_masked_button)
        customer_buttons.addWidget(load_unmasked_button)
        customer_buttons.addWidget(import_customers_button)
        customer_buttons.addWidget(refresh_customers_button)

        insurance_form = QFormLayout()
        insurance_form.addRow("대상 보험 ID", self.selected_insurance_id_input)
        insurance_form.addRow("고객 ID", self.insurance_customer_id_input)
        insurance_form.addRow("계약일자", self.contract_date_input)
        insurance_form.addRow("보험사", self.company_input)
        insurance_form.addRow("증권번호", self.policy_number_input)
        insurance_form.addRow("상품명", self.product_name_input)
        insurance_form.addRow("보험료", self.premium_input)
        insurance_form.addRow("피보험자", self.insured_person_input)
        insurance_form.addRow("결제일", self.payment_day_input)
        insurance_form.addRow("수익자", self.beneficiary_input)

        add_insurance_button = QPushButton("보험 추가")
        add_insurance_button.clicked.connect(self.create_insurance)

        update_insurance_button = QPushButton("보험 수정")
        update_insurance_button.clicked.connect(self.update_insurance)

        delete_insurance_button = QPushButton("보험 삭제")
        delete_insurance_button.clicked.connect(self.delete_insurance)

        import_insurances_button = QPushButton("보험 CSV 가져오기")
        import_insurances_button.clicked.connect(self.import_insurances_from_csv)

        refresh_insurances_button = QPushButton("보험 목록 새로고침")
        refresh_insurances_button.clicked.connect(self.refresh_insurances)

        insurance_buttons = QHBoxLayout()
        insurance_buttons.addWidget(add_insurance_button)
        insurance_buttons.addWidget(update_insurance_button)
        insurance_buttons.addWidget(delete_insurance_button)
        insurance_buttons.addWidget(import_insurances_button)
        insurance_buttons.addWidget(refresh_insurances_button)

        self.customers_table = QTableWidget(0, 6)
        self.customers_table.setHorizontalHeaderLabels(
            ["ID", "이름", "주민번호", "연락처", "직업", "결제계좌"]
        )
        self.customers_table.cellClicked.connect(self._on_customer_row_selected)

        self.insurances_table = QTableWidget(0, 8)
        self.insurances_table.setHorizontalHeaderLabels(
            ["ID", "고객ID", "계약일자", "보험사", "증권번호", "상품명", "보험료", "결제일"]
        )
        self.insurances_table.cellClicked.connect(self._on_insurance_row_selected)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("고객 입력/수정"))
        left_layout.addLayout(customer_form)
        left_layout.addLayout(customer_buttons)
        left_layout.addWidget(QLabel("보험 입력/수정"))
        left_layout.addLayout(insurance_form)
        left_layout.addLayout(insurance_buttons)

        right_panel = QWidget()
        right_layout = QGridLayout(right_panel)
        right_layout.addWidget(QLabel("고객 목록(민감정보 마스킹)"), 0, 0)
        right_layout.addWidget(self.customers_table, 1, 0)
        right_layout.addWidget(QLabel("보험 목록(선택 고객 기준)"), 2, 0)
        right_layout.addWidget(self.insurances_table, 3, 0)

        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.addWidget(left_panel, 1)
        central_layout.addWidget(right_panel, 2)
        self.setCentralWidget(central)

    def _selected_customer_id(self) -> int:
        raw_id = self.selected_customer_id_input.text().strip()
        if not raw_id:
            raise ValueError("대상 고객 ID를 입력하세요.")
        return int(raw_id)

    def _selected_insurance_id(self) -> int:
        raw_id = self.selected_insurance_id_input.text().strip()
        if not raw_id:
            raise ValueError("대상 보험 ID를 입력하세요.")
        return int(raw_id)

    def _insurance_payload_from_form(self) -> InsuranceCreate:
        customer_id_raw = self.insurance_customer_id_input.text().strip()
        if not customer_id_raw:
            raise ValueError("보험 고객 ID를 입력하세요.")

        return InsuranceCreate(
            customer_id=int(customer_id_raw),
            contract_date=datetime.strptime(self.contract_date_input.text().strip(), "%Y-%m-%d").date(),
            company=self.company_input.text(),
            policy_number=self.policy_number_input.text(),
            product_name=self.product_name_input.text(),
            premium=Decimal(self.premium_input.text().strip()),
            insured_person=self.insured_person_input.text(),
            payment_day=int(self.payment_day_input.text().strip()),
            beneficiary=self.beneficiary_input.text(),
        )

    def _customer_payload_from_form(self) -> CustomerCreate:
        return CustomerCreate(
            name=self.name_input.text(),
            rrn=self.rrn_input.text(),
            phone=self.phone_input.text(),
            address=self.address_input.text(),
            job=self.job_input.text(),
            payment_card=self.card_input.text(),
            payment_account=self.account_input.text(),
            payout_account=self.payout_input.text(),
            medical_history=self.medical_input.text(),
            note=self.note_input.text(),
        )

    def _on_customer_row_selected(self, row: int, _column: int) -> None:
        item = self.customers_table.item(row, 0)
        if item is None:
            return

        selected_id = item.text()
        self.selected_customer_id_input.setText(selected_id)
        self.insurance_customer_id_input.setText(selected_id)
        self.refresh_insurances()

    def _on_insurance_row_selected(self, row: int, _column: int) -> None:
        insurance_item = self.insurances_table.item(row, 0)
        customer_item = self.insurances_table.item(row, 1)
        if insurance_item is not None:
            self.selected_insurance_id_input.setText(insurance_item.text())
        if customer_item is not None:
            self.insurance_customer_id_input.setText(customer_item.text())

    def create_customer(self) -> None:
        try:
            customer_id = self.customer_service.create_customer(self._customer_payload_from_form())
            QMessageBox.information(self, "완료", f"고객이 등록되었습니다. ID={customer_id}")
            self.refresh_customers()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def _fill_customer_form(self, customer) -> None:
        self.name_input.setText(customer.name)
        self.rrn_input.setText(customer.rrn)
        self.phone_input.setText(customer.phone)
        self.address_input.setText(customer.address)
        self.job_input.setText(customer.job)
        self.card_input.setText(customer.payment_card)
        self.account_input.setText(customer.payment_account)
        self.payout_input.setText(customer.payout_account)
        self.medical_input.setText(customer.medical_history)
        self.note_input.setText(customer.note)

    def load_customer_masked(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            customer = self.customer_service.get_customer(customer_id, reveal_sensitive=False)
            self._fill_customer_form(customer)
            QMessageBox.information(self, "완료", "마스킹된 고객 정보를 불러왔습니다.")
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def load_customer_unmasked(self) -> None:
        confirm = QMessageBox.question(
            self,
            "민감정보 확인",
            "민감정보를 마스킹 해제하여 표시합니다. 계속할까요?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            customer_id = self._selected_customer_id()
            customer = self.customer_service.get_customer(customer_id, reveal_sensitive=True)
            self._fill_customer_form(customer)
            QMessageBox.information(self, "완료", "민감정보가 해제된 고객 정보를 불러왔습니다.")
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def update_customer(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            self.customer_service.update_customer(customer_id, self._customer_payload_from_form())
            QMessageBox.information(self, "완료", f"고객(ID={customer_id})이 수정되었습니다.")
            self.refresh_customers()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def delete_customer(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            self.customer_service.delete_customer(customer_id)
            QMessageBox.information(self, "완료", f"고객(ID={customer_id})이 삭제되었습니다.")
            self.refresh_customers()
            self.insurances_table.setRowCount(0)
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def create_insurance(self) -> None:
        try:
            insurance_id = self.insurance_service.create_insurance(self._insurance_payload_from_form())
            QMessageBox.information(self, "완료", f"보험이 등록되었습니다. ID={insurance_id}")
            self.refresh_insurances()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def update_insurance(self) -> None:
        try:
            insurance_id = self._selected_insurance_id()
            self.insurance_service.update_insurance(insurance_id, self._insurance_payload_from_form())
            QMessageBox.information(self, "완료", f"보험(ID={insurance_id})이 수정되었습니다.")
            self.refresh_insurances()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def delete_insurance(self) -> None:
        try:
            insurance_id = self._selected_insurance_id()
            self.insurance_service.delete_insurance(insurance_id)
            QMessageBox.information(self, "완료", f"보험(ID={insurance_id})이 삭제되었습니다.")
            self.refresh_insurances()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def refresh_customers(self) -> None:
        task = LoadCustomersTask(self.customer_service, self.customer_limit, self.customer_offset)
        task.signals.done.connect(self._render_customers)
        task.signals.error.connect(lambda message: QMessageBox.critical(self, "오류", message))
        self.thread_pool.start(task)

    def refresh_insurances(self) -> None:
        raw_customer_id = self.insurance_customer_id_input.text().strip()
        if not raw_customer_id:
            self.insurances_table.setRowCount(0)
            return

        try:
            customer_id = int(raw_customer_id)
        except ValueError:
            QMessageBox.critical(self, "오류", "보험 고객 ID는 숫자여야 합니다.")
            return

        task = LoadInsurancesTask(
            self.insurance_service,
            customer_id,
            self.insurance_limit,
            self.insurance_offset,
        )
        task.signals.done.connect(self._render_insurances)
        task.signals.error.connect(lambda message: QMessageBox.critical(self, "오류", message))
        self.thread_pool.start(task)

    def import_customers_from_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "고객 CSV 선택", "", "CSV Files (*.csv)")
        if not file_path:
            return

        task = ImportCustomersCsvTask(self.csv_import_service, file_path)
        task.signals.done.connect(self._show_customer_import_result)
        task.signals.error.connect(lambda message: QMessageBox.critical(self, "CSV 오류", message))
        self.thread_pool.start(task)

    def import_insurances_from_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "보험 CSV 선택", "", "CSV Files (*.csv)")
        if not file_path:
            return

        task = ImportInsurancesCsvTask(self.csv_import_service, file_path)
        task.signals.done.connect(self._show_insurance_import_result)
        task.signals.error.connect(lambda message: QMessageBox.critical(self, "CSV 오류", message))
        self.thread_pool.start(task)

    def _show_customer_import_result(self, created_count: int, failed_count: int, details: str) -> None:
        message = f"고객 CSV 등록 완료\n성공: {created_count}건\n실패: {failed_count}건"
        if details:
            message += f"\n\n실패 상세(최대 10건)\n{details}"
        QMessageBox.information(self, "CSV 결과", message)
        self.refresh_customers()

    def _show_insurance_import_result(self, created_count: int, failed_count: int, details: str) -> None:
        message = f"보험 CSV 등록 완료\n성공: {created_count}건\n실패: {failed_count}건"
        if details:
            message += f"\n\n실패 상세(최대 10건)\n{details}"
        QMessageBox.information(self, "CSV 결과", message)
        self.refresh_insurances()

    def _render_customers(self, customers: list) -> None:
        self.customers_table.setRowCount(len(customers))
        for row_index, customer in enumerate(customers):
            data = asdict(customer)
            self.customers_table.setItem(row_index, 0, QTableWidgetItem(str(data["id"])))
            self.customers_table.setItem(row_index, 1, QTableWidgetItem(data["name"]))
            self.customers_table.setItem(row_index, 2, QTableWidgetItem(data["rrn"]))
            self.customers_table.setItem(row_index, 3, QTableWidgetItem(data["phone"]))
            self.customers_table.setItem(row_index, 4, QTableWidgetItem(data["job"]))
            self.customers_table.setItem(row_index, 5, QTableWidgetItem(data["payment_account"]))

    def _render_insurances(self, insurances: list) -> None:
        self.insurances_table.setRowCount(len(insurances))
        for row_index, insurance in enumerate(insurances):
            data = asdict(insurance)
            self.insurances_table.setItem(row_index, 0, QTableWidgetItem(str(data["id"])))
            self.insurances_table.setItem(row_index, 1, QTableWidgetItem(str(data["customer_id"])))
            self.insurances_table.setItem(row_index, 2, QTableWidgetItem(data["contract_date"]))
            self.insurances_table.setItem(row_index, 3, QTableWidgetItem(data["company"]))
            self.insurances_table.setItem(row_index, 4, QTableWidgetItem(data["policy_number"]))
            self.insurances_table.setItem(row_index, 5, QTableWidgetItem(data["product_name"]))
            self.insurances_table.setItem(row_index, 6, QTableWidgetItem(data["premium"]))
            self.insurances_table.setItem(row_index, 7, QTableWidgetItem(str(data["payment_day"])))
