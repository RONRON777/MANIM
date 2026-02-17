"""Main GUI window for customer and insurance management."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
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


class ImportSignals(QObject):
    """Signals for background CSV import."""

    done = Signal(int, int, str)
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
    """GUI for customer/insurance management."""

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
        self.resize(1400, 900)

        self.tabs = QTabWidget()
        self._build_customer_tab()
        self._build_insurance_tab()
        self._build_query_tab()
        self._build_exit_tab()
        self.setCentralWidget(self.tabs)

        self.refresh_next_ids()
        self.refresh_customers()

    def _build_customer_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        self.customer_next_id_input = QLineEdit()
        self.customer_next_id_input.setReadOnly(True)
        self.selected_customer_id_input = QLineEdit()

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

        form.addRow("다음 고객 ID", self.customer_next_id_input)
        form.addRow("수정/삭제 대상 ID", self.selected_customer_id_input)
        form.addRow("이름", self.name_input)
        form.addRow("주민번호", self.rrn_input)
        form.addRow("연락처", self.phone_input)
        form.addRow("주소", self.address_input)
        form.addRow("직업", self.job_input)
        form.addRow("카드번호(선택)", self.card_input)
        form.addRow("결제 계좌(선택)", self.account_input)
        form.addRow("보험금 수령 계좌(선택)", self.payout_input)
        form.addRow("병력", self.medical_input)
        form.addRow("비고", self.note_input)

        buttons = QHBoxLayout()
        add_button = QPushButton("고객 추가")
        add_button.clicked.connect(self.create_customer)
        update_button = QPushButton("고객 수정")
        update_button.clicked.connect(self.update_customer)
        delete_button = QPushButton("고객 삭제")
        delete_button.clicked.connect(self.delete_customer)
        clear_button = QPushButton("칸 비우기")
        clear_button.clicked.connect(self.clear_customer_form)
        import_button = QPushButton("고객 CSV 가져오기")
        import_button.clicked.connect(self.import_customers_from_csv)
        refresh_button = QPushButton("목록 새로고침")
        refresh_button.clicked.connect(self.refresh_customers)

        buttons.addWidget(add_button)
        buttons.addWidget(update_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(clear_button)
        buttons.addWidget(import_button)
        buttons.addWidget(refresh_button)

        self.customers_table = QTableWidget(0, 6)
        self.customers_table.setHorizontalHeaderLabels(
            ["ID", "이름", "주민번호", "연락처", "직업", "결제계좌"]
        )
        self.customers_table.cellClicked.connect(self._on_customer_row_selected)

        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("고객 목록(민감정보 마스킹)"))
        layout.addWidget(self.customers_table)

        self.tabs.addTab(tab, "고객 관리")

    def _build_insurance_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        self.insurance_next_id_input = QLineEdit()
        self.insurance_next_id_input.setReadOnly(True)
        self.selected_insurance_id_input = QLineEdit()
        self.insurance_customer_id_input = QLineEdit()

        self.contract_date_input = QLineEdit()
        self.contract_date_input.setPlaceholderText("YYYY-MM-DD")
        self.company_input = QLineEdit()
        self.policy_number_input = QLineEdit()
        self.product_name_input = QLineEdit()
        self.premium_input = QLineEdit()
        self.insured_person_input = QLineEdit()
        self.payment_day_input = QLineEdit()
        self.beneficiary_input = QLineEdit()

        form.addRow("다음 보험 ID", self.insurance_next_id_input)
        form.addRow("수정/삭제 대상 ID", self.selected_insurance_id_input)
        form.addRow("고객 ID", self.insurance_customer_id_input)
        form.addRow("계약일자", self.contract_date_input)
        form.addRow("보험사", self.company_input)
        form.addRow("증권번호", self.policy_number_input)
        form.addRow("상품명", self.product_name_input)
        form.addRow("보험료", self.premium_input)
        form.addRow("피보험자", self.insured_person_input)
        form.addRow("결제일", self.payment_day_input)
        form.addRow("수익자", self.beneficiary_input)

        buttons = QHBoxLayout()
        add_button = QPushButton("보험 추가")
        add_button.clicked.connect(self.create_insurance)
        update_button = QPushButton("보험 수정")
        update_button.clicked.connect(self.update_insurance)
        delete_button = QPushButton("보험 삭제")
        delete_button.clicked.connect(self.delete_insurance)
        clear_button = QPushButton("칸 비우기")
        clear_button.clicked.connect(self.clear_insurance_form)
        import_button = QPushButton("보험 CSV 가져오기")
        import_button.clicked.connect(self.import_insurances_from_csv)
        refresh_button = QPushButton("목록 새로고침")
        refresh_button.clicked.connect(self.refresh_insurances)

        buttons.addWidget(add_button)
        buttons.addWidget(update_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(clear_button)
        buttons.addWidget(import_button)
        buttons.addWidget(refresh_button)

        self.insurances_table = QTableWidget(0, 8)
        self.insurances_table.setHorizontalHeaderLabels(
            ["ID", "고객ID", "계약일자", "보험사", "증권번호", "상품명", "보험료", "결제일"]
        )
        self.insurances_table.cellClicked.connect(self._on_insurance_row_selected)

        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("보험 목록(입력 고객 ID 기준)"))
        layout.addWidget(self.insurances_table)

        self.tabs.addTab(tab, "보험 관리")

    def _build_query_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        customer_query_row = QHBoxLayout()
        self.customer_search_field = QComboBox()
        self.customer_search_field.addItem("고객 ID", "id")
        self.customer_search_field.addItem("이름", "name")
        self.customer_search_field.addItem("연락처", "phone")
        self.customer_search_field.addItem("주소", "address")
        self.customer_search_field.addItem("직업", "job")
        self.customer_search_keyword = QLineEdit()
        self.customer_search_keyword.setPlaceholderText("고객 검색어")
        customer_search_button = QPushButton("고객 검색")
        customer_search_button.clicked.connect(self.search_customers)
        customer_query_row.addWidget(QLabel("고객 검색"))
        customer_query_row.addWidget(self.customer_search_field)
        customer_query_row.addWidget(self.customer_search_keyword)
        customer_query_row.addWidget(customer_search_button)

        self.query_customers_table = QTableWidget(0, 6)
        self.query_customers_table.setHorizontalHeaderLabels(
            ["ID", "이름", "주민번호", "연락처", "직업", "결제계좌"]
        )

        insurance_query_row = QHBoxLayout()
        self.insurance_search_field = QComboBox()
        self.insurance_search_field.addItem("보험 ID", "id")
        self.insurance_search_field.addItem("고객 ID", "customer_id")
        self.insurance_search_field.addItem("보험사", "company")
        self.insurance_search_field.addItem("증권번호", "policy_number")
        self.insurance_search_field.addItem("상품명", "product_name")
        self.insurance_search_field.addItem("피보험자", "insured_person")
        self.insurance_search_field.addItem("수익자", "beneficiary")
        self.insurance_search_keyword = QLineEdit()
        self.insurance_search_keyword.setPlaceholderText("보험 검색어")
        insurance_search_button = QPushButton("보험 검색")
        insurance_search_button.clicked.connect(self.search_insurances)
        insurance_query_row.addWidget(QLabel("보험 검색"))
        insurance_query_row.addWidget(self.insurance_search_field)
        insurance_query_row.addWidget(self.insurance_search_keyword)
        insurance_query_row.addWidget(insurance_search_button)

        self.query_insurances_table = QTableWidget(0, 8)
        self.query_insurances_table.setHorizontalHeaderLabels(
            ["ID", "고객ID", "계약일자", "보험사", "증권번호", "상품명", "보험료", "결제일"]
        )

        layout.addLayout(customer_query_row)
        layout.addWidget(self.query_customers_table)
        layout.addLayout(insurance_query_row)
        layout.addWidget(self.query_insurances_table)

        self.tabs.addTab(tab, "조회")

    def _build_exit_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        exit_button = QPushButton("프로그램 종료")
        exit_button.clicked.connect(self.close)
        layout.addWidget(QLabel("작업을 마쳤으면 종료 버튼을 눌러주세요."))
        layout.addWidget(exit_button)
        self.tabs.addTab(tab, "종료")

    def refresh_next_ids(self) -> None:
        try:
            next_customer_id = self.customer_service.next_customer_id()
            self.customer_next_id_input.setText(str(next_customer_id))
            if not self.selected_customer_id_input.text().strip():
                self.selected_customer_id_input.setText(str(next_customer_id))

            next_insurance_id = self.insurance_service.next_insurance_id()
            self.insurance_next_id_input.setText(str(next_insurance_id))
            if not self.selected_insurance_id_input.text().strip():
                self.selected_insurance_id_input.setText(str(next_insurance_id))
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def _selected_customer_id(self) -> int:
        raw = self.selected_customer_id_input.text().strip()
        if not raw:
            raise ValueError("수정/삭제 대상 고객 ID를 입력하세요.")
        return int(raw)

    def _selected_insurance_id(self) -> int:
        raw = self.selected_insurance_id_input.text().strip()
        if not raw:
            raise ValueError("수정/삭제 대상 보험 ID를 입력하세요.")
        return int(raw)

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

    def _insurance_payload_from_form(self) -> InsuranceCreate:
        customer_id_raw = self.insurance_customer_id_input.text().strip()
        if not customer_id_raw:
            customer_id_raw = self.selected_customer_id_input.text().strip()
        if not customer_id_raw:
            raise ValueError("고객 ID를 입력하세요.")

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

    def create_customer(self) -> None:
        try:
            customer_id = self.customer_service.create_customer(self._customer_payload_from_form())
            QMessageBox.information(self, "완료", f"고객이 등록되었습니다. ID={customer_id}")
            self.clear_customer_form()
            self.refresh_customers()
            self.refresh_next_ids()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def update_customer(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            self.customer_service.update_customer(customer_id, self._customer_payload_from_form())
            QMessageBox.information(self, "완료", f"고객(ID={customer_id}) 수정 완료")
            self.refresh_customers()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def delete_customer(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            self.customer_service.delete_customer(customer_id)
            QMessageBox.information(self, "완료", f"고객(ID={customer_id}) 삭제 완료")
            self.refresh_customers()
            self.insurances_table.setRowCount(0)
            self.refresh_next_ids()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def create_insurance(self) -> None:
        try:
            insurance_id = self.insurance_service.create_insurance(self._insurance_payload_from_form())
            QMessageBox.information(self, "완료", f"보험이 등록되었습니다. ID={insurance_id}")
            self.clear_insurance_form(keep_customer_id=True)
            self.refresh_insurances()
            self.refresh_next_ids()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def update_insurance(self) -> None:
        try:
            insurance_id = self._selected_insurance_id()
            self.insurance_service.update_insurance(insurance_id, self._insurance_payload_from_form())
            QMessageBox.information(self, "완료", f"보험(ID={insurance_id}) 수정 완료")
            self.refresh_insurances()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def delete_insurance(self) -> None:
        try:
            insurance_id = self._selected_insurance_id()
            self.insurance_service.delete_insurance(insurance_id)
            QMessageBox.information(self, "완료", f"보험(ID={insurance_id}) 삭제 완료")
            self.refresh_insurances()
            self.refresh_next_ids()
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
            QMessageBox.critical(self, "오류", "고객 ID는 숫자여야 합니다.")
            return

        task = LoadInsurancesTask(self.insurance_service, customer_id, self.insurance_limit, self.insurance_offset)
        task.signals.done.connect(self._render_insurances)
        task.signals.error.connect(lambda message: QMessageBox.critical(self, "오류", message))
        self.thread_pool.start(task)

    def search_customers(self) -> None:
        try:
            field = self.customer_search_field.currentData()
            keyword = self.customer_search_keyword.text().strip()
            if keyword:
                customers = self.customer_service.search_customers(field=field, keyword=keyword)
            else:
                customers = self.customer_service.list_customers(limit=100, offset=0)
            self._render_customer_table(self.query_customers_table, customers)
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "검색 오류", str(error))

    def search_insurances(self) -> None:
        try:
            field = self.insurance_search_field.currentData()
            keyword = self.insurance_search_keyword.text().strip()
            if keyword:
                insurances = self.insurance_service.search_insurances(field=field, keyword=keyword)
            else:
                self.query_insurances_table.setRowCount(0)
                return
            self._render_insurance_table(self.query_insurances_table, insurances)
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "검색 오류", str(error))

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
        self.refresh_next_ids()

    def _show_insurance_import_result(self, created_count: int, failed_count: int, details: str) -> None:
        message = f"보험 CSV 등록 완료\n성공: {created_count}건\n실패: {failed_count}건"
        if details:
            message += f"\n\n실패 상세(최대 10건)\n{details}"
        QMessageBox.information(self, "CSV 결과", message)
        self.refresh_insurances()
        self.refresh_next_ids()

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

    def clear_customer_form(self) -> None:
        self.name_input.clear()
        self.rrn_input.clear()
        self.phone_input.clear()
        self.address_input.clear()
        self.job_input.clear()
        self.card_input.clear()
        self.account_input.clear()
        self.payout_input.clear()
        self.medical_input.clear()
        self.note_input.clear()
        self.selected_customer_id_input.setText(self.customer_next_id_input.text())

    def clear_insurance_form(self, keep_customer_id: bool = False) -> None:
        self.selected_insurance_id_input.setText(self.insurance_next_id_input.text())
        if not keep_customer_id:
            self.insurance_customer_id_input.clear()
        self.contract_date_input.clear()
        self.company_input.clear()
        self.policy_number_input.clear()
        self.product_name_input.clear()
        self.premium_input.clear()
        self.insured_person_input.clear()
        self.payment_day_input.clear()
        self.beneficiary_input.clear()

    def _render_customers(self, customers: list) -> None:
        self._render_customer_table(self.customers_table, customers)

    def _render_insurances(self, insurances: list) -> None:
        self._render_insurance_table(self.insurances_table, insurances)

    @staticmethod
    def _render_customer_table(table: QTableWidget, customers: list) -> None:
        table.setRowCount(len(customers))
        for row_index, customer in enumerate(customers):
            data = asdict(customer)
            table.setItem(row_index, 0, QTableWidgetItem(str(data["id"])))
            table.setItem(row_index, 1, QTableWidgetItem(data["name"]))
            table.setItem(row_index, 2, QTableWidgetItem(data["rrn"]))
            table.setItem(row_index, 3, QTableWidgetItem(data["phone"]))
            table.setItem(row_index, 4, QTableWidgetItem(data["job"]))
            table.setItem(row_index, 5, QTableWidgetItem(data["payment_account"]))

    @staticmethod
    def _render_insurance_table(table: QTableWidget, insurances: list) -> None:
        table.setRowCount(len(insurances))
        for row_index, insurance in enumerate(insurances):
            data = asdict(insurance)
            table.setItem(row_index, 0, QTableWidgetItem(str(data["id"])))
            table.setItem(row_index, 1, QTableWidgetItem(str(data["customer_id"])))
            table.setItem(row_index, 2, QTableWidgetItem(data["contract_date"]))
            table.setItem(row_index, 3, QTableWidgetItem(data["company"]))
            table.setItem(row_index, 4, QTableWidgetItem(data["policy_number"]))
            table.setItem(row_index, 5, QTableWidgetItem(data["product_name"]))
            table.setItem(row_index, 6, QTableWidgetItem(data["premium"]))
            table.setItem(row_index, 7, QTableWidgetItem(str(data["payment_day"])))
