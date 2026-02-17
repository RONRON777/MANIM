"""Main GUI window for customer and insurance management."""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QFrame,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from manim_app.models.customer import CustomerCreate
from manim_app.models.insurance import InsuranceCreate
from manim_app.repositories.audit_repository import AuditRepository
from manim_app.services.csv_import_service import CsvImportService
from manim_app.services.customer_service import CustomerService
from manim_app.services.insurance_service import InsuranceService
from manim_app.ui.tasks import (
    ImportCustomersCsvTask,
    ImportInsurancesCsvTask,
    LoadAuditLogsTask,
    LoadCustomersTask,
    LoadInsurancesTask,
)


class MainWindow(QMainWindow):
    """GUI for customer/insurance management."""

    def __init__(
        self,
        customer_service: CustomerService,
        insurance_service: InsuranceService,
        csv_import_service: CsvImportService,
        audit_repo: AuditRepository,
    ):
        super().__init__()
        self.customer_service = customer_service
        self.insurance_service = insurance_service
        self.csv_import_service = csv_import_service
        self.audit_repo = audit_repo
        self.thread_pool = QThreadPool.globalInstance()

        self.customer_limit = 50
        self.customer_offset = 0
        self.insurance_limit = 50
        self.insurance_offset = 0
        self.audit_limit = 300
        self._audit_details: list[str] = []
        self._audit_rows: list[dict] = []

        self.setWindowTitle("MANIM - 보험 고객 관리")
        self.resize(1400, 900)

        self.tabs = QTabWidget()
        self._build_customer_tab()
        self._build_insurance_tab()
        self._build_query_tab()
        self._build_delete_tab()
        self._build_history_tab()
        self._build_help_tab()
        self._build_exit_tab()
        self.setCentralWidget(self.tabs)

        self.refresh_customers()
        self.refresh_audit_logs()

    def _build_customer_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        self.customer_id_input = QLineEdit()

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

        for widget in [
            self.name_input,
            self.rrn_input,
            self.phone_input,
            self.address_input,
            self.job_input,
            self.card_input,
            self.account_input,
            self.payout_input,
            self.medical_input,
            self.note_input,
        ]:
            widget.returnPressed.connect(self.create_customer)

        form.addRow("고객 ID", self.customer_id_input)
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
        restore_button = QPushButton("삭제 고객 복구")
        restore_button.clicked.connect(self.restore_customer)
        clear_button = QPushButton("칸 비우기")
        clear_button.clicked.connect(self.clear_customer_form)
        import_button = QPushButton("고객 CSV 가져오기")
        import_button.clicked.connect(self.import_customers_from_csv)
        refresh_button = QPushButton("목록 새로고침")
        refresh_button.clicked.connect(self.refresh_customers)

        buttons.addWidget(add_button)
        buttons.addWidget(update_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(restore_button)
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
        self.insurance_id_input = QLineEdit()
        self.insurance_customer_id_input = QLineEdit()
        self.insurance_customer_selector = QComboBox()
        self.insurance_customer_selector.setEditable(True)
        self.insurance_customer_selector.lineEdit().setPlaceholderText("고객명/ID 검색 선택")
        self.insurance_customer_selector.currentIndexChanged.connect(
            self._on_customer_selector_changed
        )

        self.contract_date_input = QLineEdit()
        self.contract_date_input.setPlaceholderText("YYYY-MM-DD")
        self.contract_date_input.setText(date.today().isoformat())
        self.company_input = QLineEdit()
        self.policy_number_input = QLineEdit()
        self.product_name_input = QLineEdit()
        self.premium_input = QLineEdit()
        self.insured_person_input = QLineEdit()
        self.payment_day_input = QLineEdit()
        self.payment_day_input.setText("25")
        self.beneficiary_input = QLineEdit()

        for widget in [
            self.contract_date_input,
            self.company_input,
            self.policy_number_input,
            self.product_name_input,
            self.premium_input,
            self.insured_person_input,
            self.payment_day_input,
            self.beneficiary_input,
        ]:
            widget.returnPressed.connect(self.create_insurance)

        form.addRow("보험 ID", self.insurance_id_input)
        customer_row = QHBoxLayout()
        customer_row.addWidget(self.insurance_customer_id_input)
        customer_row.addWidget(self.insurance_customer_selector)
        form.addRow("고객 ID", customer_row)
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
            [
                "ID",
                "고객ID",
                "계약일자",
                "보험사",
                "증권번호",
                "상품명",
                "보험료",
                "결제일",
            ]
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
        self.customer_search_keyword.returnPressed.connect(self.search_customers)
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
        self.insurance_search_keyword.returnPressed.connect(self.search_insurances)
        insurance_search_button = QPushButton("보험 검색")
        insurance_search_button.clicked.connect(self.search_insurances)
        insurance_query_row.addWidget(QLabel("보험 검색"))
        insurance_query_row.addWidget(self.insurance_search_field)
        insurance_query_row.addWidget(self.insurance_search_keyword)
        insurance_query_row.addWidget(insurance_search_button)

        self.query_insurances_table = QTableWidget(0, 8)
        self.query_insurances_table.setHorizontalHeaderLabels(
            [
                "ID",
                "고객ID",
                "계약일자",
                "보험사",
                "증권번호",
                "상품명",
                "보험료",
                "결제일",
            ]
        )

        layout.addLayout(customer_query_row)
        layout.addWidget(self.query_customers_table)
        layout.addLayout(insurance_query_row)
        layout.addWidget(self.query_insurances_table)

        self.tabs.addTab(tab, "조회")

    def _build_delete_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        customer_row = QHBoxLayout()
        self.delete_customer_id_input = QLineEdit()
        self.delete_customer_id_input.setPlaceholderText("영구삭제할 고객 ID")
        delete_customer_button = QPushButton("고객 영구 삭제")
        delete_customer_button.clicked.connect(self.hard_delete_customer)
        customer_row.addWidget(self.delete_customer_id_input)
        customer_row.addWidget(delete_customer_button)

        insurance_row = QHBoxLayout()
        self.delete_insurance_id_input = QLineEdit()
        self.delete_insurance_id_input.setPlaceholderText("영구삭제할 보험 ID")
        delete_insurance_button = QPushButton("보험 영구 삭제")
        delete_insurance_button.clicked.connect(self.hard_delete_insurance)
        insurance_row.addWidget(self.delete_insurance_id_input)
        insurance_row.addWidget(delete_insurance_button)

        purge_button = QPushButton("DB 전체 비우기 (soft delete 포함)")
        purge_button.clicked.connect(self.purge_all_data)

        layout.addWidget(QLabel("영구 삭제는 되돌릴 수 없습니다."))
        layout.addLayout(customer_row)
        layout.addLayout(insurance_row)
        layout.addWidget(purge_button)

        self.tabs.addTab(tab, "삭제")

    def _build_history_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        filter_row = QHBoxLayout()
        self.log_action_filter = QComboBox()
        self.log_action_filter.addItem("전체 액션", "")
        self.log_action_filter.addItem("CREATE", "CREATE")
        self.log_action_filter.addItem("READ", "READ")
        self.log_action_filter.addItem("UPDATE", "UPDATE")
        self.log_action_filter.addItem("DELETE", "DELETE")

        self.log_entity_filter = QComboBox()
        self.log_entity_filter.addItem("전체 엔티티", "")
        self.log_entity_filter.addItem("customer", "customer")
        self.log_entity_filter.addItem("insurance", "insurance")

        self.log_keyword_input = QLineEdit()
        self.log_keyword_input.setPlaceholderText("상세 검색어")
        self.log_keyword_input.returnPressed.connect(self.refresh_audit_logs)

        self.log_period_filter = QComboBox()
        self.log_period_filter.addItem("전체", "all")
        self.log_period_filter.addItem("오늘", "today")
        self.log_period_filter.addItem("최근 7일", "7d")
        self.log_period_filter.addItem("최근 30일", "30d")
        self.log_period_filter.addItem("직접 지정", "custom")
        self.log_period_filter.currentIndexChanged.connect(self._on_period_changed)

        self.log_date_from_input = QLineEdit()
        self.log_date_from_input.setPlaceholderText("시작일 YYYY-MM-DD")
        self.log_date_to_input = QLineEdit()
        self.log_date_to_input.setPlaceholderText("종료일 YYYY-MM-DD")
        self.log_date_from_input.returnPressed.connect(self.refresh_audit_logs)
        self.log_date_to_input.returnPressed.connect(self.refresh_audit_logs)
        self.log_date_from_input.setEnabled(False)
        self.log_date_to_input.setEnabled(False)

        refresh_button = QPushButton("이력 조회")
        refresh_button.clicked.connect(self.refresh_audit_logs)
        export_button = QPushButton("CSV 내보내기")
        export_button.clicked.connect(self.export_audit_logs_csv)

        filter_row.addWidget(QLabel("액션"))
        filter_row.addWidget(self.log_action_filter)
        filter_row.addWidget(QLabel("대상"))
        filter_row.addWidget(self.log_entity_filter)
        filter_row.addWidget(QLabel("기간"))
        filter_row.addWidget(self.log_period_filter)
        filter_row.addWidget(self.log_date_from_input)
        filter_row.addWidget(self.log_date_to_input)
        filter_row.addWidget(self.log_keyword_input)
        filter_row.addWidget(refresh_button)
        filter_row.addWidget(export_button)

        self.audit_table = QTableWidget(0, 6)
        self.audit_table.setHorizontalHeaderLabels(
            ["ID", "시간", "액션", "엔티티", "대상ID", "요약"]
        )
        self.audit_table.cellClicked.connect(self._on_audit_row_selected)

        self.audit_detail_view = QPlainTextEdit()
        self.audit_detail_view.setReadOnly(True)

        layout.addLayout(filter_row)
        layout.addWidget(QLabel("작업 이력"))
        layout.addWidget(self.audit_table)
        layout.addWidget(QLabel("변경 상세"))
        layout.addWidget(self.audit_detail_view)

        self.tabs.addTab(tab, "이력")

    def _build_exit_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        exit_button = QPushButton("프로그램 종료")
        exit_button.clicked.connect(self.close)
        layout.addWidget(QLabel("작업을 마쳤으면 종료 버튼을 눌러주세요."))
        layout.addWidget(exit_button)
        self.tabs.addTab(tab, "종료")

    def _build_help_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        content = QLabel(
            """
<h2>도움말</h2>
<h3>간단 사용법</h3>
<ol>
  <li>고객 관리 탭에서 고객 정보를 입력하고 <b>고객 추가</b></li>
  <li>보험 관리 탭에서 고객 ID를 선택하고 <b>보험 추가</b></li>
  <li>조회 탭에서 필드 선택 + 검색어 입력 후 <b>Enter</b> 또는 검색 버튼</li>
</ol>

<h3>CSV 형식</h3>
<p><b>고객 CSV 헤더</b><br>
<code>이름,주민번호,연락처,주소,직업,카드번호,<br>
결제계좌,보험금수령계좌,병력,비고</code>
</p>
<p><b>보험 CSV 헤더</b><br>
<code>고객ID,계약일자,보험사,증권번호,상품명,<br>
보험료,피보험자,결제일,수익자</code>
</p>

<h3>입력 규칙</h3>
<ul>
  <li>주민번호: 13자리 + 체크섬 검증</li>
  <li>연락처: 010-####-####</li>
  <li>계약일자: YYYY-MM-DD, 미래 날짜 불가</li>
  <li>보험료: 숫자, 양수</li>
  <li>카드/계좌: 비워도 가능, 입력 시 숫자 길이 검증</li>
</ul>
"""
        )
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setWordWrap(True)
        content.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        content.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.addWidget(content)
        wrapper_layout.addStretch(1)
        scroll.setWidget(wrapper)

        layout.addWidget(scroll)
        self.tabs.addTab(tab, "도움말")

    def _selected_customer_id(self) -> int:
        raw = self.customer_id_input.text().strip()
        if not raw:
            raise ValueError("고객 ID를 입력하세요.")
        return int(raw)

    def _selected_insurance_id(self) -> int:
        raw = self.insurance_id_input.text().strip()
        if not raw:
            raise ValueError("보험 ID를 입력하세요.")
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
            customer_id_raw = self.customer_id_input.text().strip()
        if not customer_id_raw:
            raise ValueError("고객 ID를 입력하세요.")

        premium_raw = self.premium_input.text().strip()
        try:
            premium_value = Decimal(premium_raw)
        except InvalidOperation as error:
            raise ValueError(
                "보험료는 숫자로 입력하세요. 예: 50000 또는 50000.50"
            ) from error

        return InsuranceCreate(
            customer_id=int(customer_id_raw),
            contract_date=datetime.strptime(
                self.contract_date_input.text().strip(),
                "%Y-%m-%d",
            ).date(),
            company=self.company_input.text(),
            policy_number=self.policy_number_input.text(),
            product_name=self.product_name_input.text(),
            premium=premium_value,
            insured_person=self.insured_person_input.text(),
            payment_day=int(self.payment_day_input.text().strip()),
            beneficiary=self.beneficiary_input.text(),
        )

    def create_customer(self) -> None:
        try:
            customer_id = self.customer_service.create_customer(
                self._customer_payload_from_form()
            )
            QMessageBox.information(
                self,
                "완료",
                f"고객이 등록되었습니다. ID={customer_id}",
            )
            self.customer_id_input.setText(str(customer_id))
            self.clear_customer_form()
            self.refresh_customers()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def update_customer(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            self.customer_service.update_customer(customer_id, self._customer_payload_from_form())
            QMessageBox.information(self, "완료", f"고객(ID={customer_id}) 수정 완료")
            self.refresh_customers()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def delete_customer(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            self.customer_service.delete_customer(customer_id)
            QMessageBox.information(self, "완료", f"고객(ID={customer_id}) 삭제 완료")
            self.refresh_customers()
            self.insurances_table.setRowCount(0)
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def restore_customer(self) -> None:
        try:
            customer_id = self._selected_customer_id()
            self.customer_service.restore_customer(customer_id)
            QMessageBox.information(self, "완료", f"고객(ID={customer_id}) 복구 완료")
            self.refresh_customers()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def create_insurance(self) -> None:
        try:
            insurance_id = self.insurance_service.create_insurance(
                self._insurance_payload_from_form()
            )
            QMessageBox.information(
                self,
                "완료",
                f"보험이 등록되었습니다. ID={insurance_id}",
            )
            self.insurance_id_input.setText(str(insurance_id))
            self.clear_insurance_form(keep_customer_id=True)
            self.refresh_insurances()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def update_insurance(self) -> None:
        try:
            insurance_id = self._selected_insurance_id()
            self.insurance_service.update_insurance(
                insurance_id,
                self._insurance_payload_from_form(),
            )
            QMessageBox.information(self, "완료", f"보험(ID={insurance_id}) 수정 완료")
            self.refresh_insurances()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def delete_insurance(self) -> None:
        try:
            insurance_id = self._selected_insurance_id()
            self.insurance_service.delete_insurance(insurance_id)
            QMessageBox.information(self, "완료", f"보험(ID={insurance_id}) 삭제 완료")
            self.refresh_insurances()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def hard_delete_customer(self) -> None:
        try:
            customer_id = int(self.delete_customer_id_input.text().strip())
            confirm = QMessageBox.question(
                self,
                "영구 삭제 확인",
                f"고객(ID={customer_id})을 영구 삭제할까요?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self.customer_service.hard_delete_customer(customer_id)
            QMessageBox.information(
                self,
                "완료",
                f"고객(ID={customer_id}) 영구 삭제 완료",
            )
            self.refresh_customers()
            self.refresh_insurances()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def hard_delete_insurance(self) -> None:
        try:
            insurance_id = int(self.delete_insurance_id_input.text().strip())
            confirm = QMessageBox.question(
                self,
                "영구 삭제 확인",
                f"보험(ID={insurance_id})을 영구 삭제할까요?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self.insurance_service.hard_delete_insurance(insurance_id)
            QMessageBox.information(
                self,
                "완료",
                f"보험(ID={insurance_id}) 영구 삭제 완료",
            )
            self.refresh_insurances()
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def purge_all_data(self) -> None:
        confirm = QMessageBox.question(
            self,
            "DB 전체 비우기",
            "고객/보험/이력 데이터를 모두 삭제합니다. 계속할까요?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.customer_service.purge_all_customers()
            self.audit_repo.purge_all_logs()
            QMessageBox.information(self, "완료", "DB를 모두 비웠습니다.")
            self.refresh_customers()
            self.insurances_table.setRowCount(0)
            self.query_customers_table.setRowCount(0)
            self.query_insurances_table.setRowCount(0)
            self.audit_table.setRowCount(0)
            self.audit_detail_view.setPlainText("")
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "오류", str(error))

    def refresh_customers(self) -> None:
        task = LoadCustomersTask(self.customer_service, self.customer_limit, self.customer_offset)
        task.signals.done.connect(self._render_customers)
        task.signals.done.connect(self._refresh_customer_selector)
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

        task = LoadInsurancesTask(
            self.insurance_service,
            customer_id,
            self.insurance_limit,
            self.insurance_offset,
        )
        task.signals.done.connect(self._render_insurances)
        task.signals.error.connect(lambda message: QMessageBox.critical(self, "오류", message))
        self.thread_pool.start(task)

    def refresh_audit_logs(self) -> None:
        action = self.log_action_filter.currentData() or None
        entity = self.log_entity_filter.currentData() or None
        keyword = self.log_keyword_input.text().strip() or None
        date_from, date_to = self._resolve_log_date_filters()
        task = LoadAuditLogsTask(
            self.audit_repo,
            limit=self.audit_limit,
            action=action,
            entity=entity,
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
        )
        task.signals.done.connect(self._render_audit_logs)
        task.signals.error.connect(
            lambda message: QMessageBox.critical(self, "이력 오류", message)
        )
        self.thread_pool.start(task)

    def _on_period_changed(self, _index: int) -> None:
        is_custom = self.log_period_filter.currentData() == "custom"
        self.log_date_from_input.setEnabled(is_custom)
        self.log_date_to_input.setEnabled(is_custom)
        if not is_custom:
            self.log_date_from_input.clear()
            self.log_date_to_input.clear()

    def _resolve_log_date_filters(self) -> tuple[str | None, str | None]:
        period = self.log_period_filter.currentData()
        today = date.today()
        if period == "today":
            d = today.isoformat()
            return d, d
        if period == "7d":
            return (today - timedelta(days=6)).isoformat(), today.isoformat()
        if period == "30d":
            return (today - timedelta(days=29)).isoformat(), today.isoformat()
        if period == "custom":
            date_from = self.log_date_from_input.text().strip() or None
            date_to = self.log_date_to_input.text().strip() or None
            return date_from, date_to
        return None, None

    def search_customers(self) -> None:
        try:
            field = self.customer_search_field.currentData()
            keyword = self.customer_search_keyword.text().strip()
            if keyword:
                customers = self.customer_service.search_customers(field=field, keyword=keyword)
            else:
                customers = self.customer_service.list_customers(limit=100, offset=0)
            self._render_customer_table(self.query_customers_table, customers)
            self.refresh_audit_logs()
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
            self.refresh_audit_logs()
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "검색 오류", str(error))

    def import_customers_from_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "고객 CSV 선택",
            "",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        task = ImportCustomersCsvTask(self.csv_import_service, file_path)
        task.signals.done.connect(self._show_customer_import_result)
        task.signals.error.connect(
            lambda message: QMessageBox.critical(self, "CSV 오류", message)
        )
        self.thread_pool.start(task)

    def import_insurances_from_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "보험 CSV 선택",
            "",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        task = ImportInsurancesCsvTask(self.csv_import_service, file_path)
        task.signals.done.connect(self._show_insurance_import_result)
        task.signals.error.connect(
            lambda message: QMessageBox.critical(self, "CSV 오류", message)
        )
        self.thread_pool.start(task)

    def _show_customer_import_result(
        self,
        created_count: int,
        failed_count: int,
        details: str,
    ) -> None:
        message = f"고객 CSV 등록 완료\n성공: {created_count}건\n실패: {failed_count}건"
        if details:
            message += f"\n\n실패 상세(최대 10건)\n{details}"
        QMessageBox.information(self, "CSV 결과", message)
        self.refresh_customers()
        self.refresh_audit_logs()

    def _show_insurance_import_result(
        self,
        created_count: int,
        failed_count: int,
        details: str,
    ) -> None:
        message = f"보험 CSV 등록 완료\n성공: {created_count}건\n실패: {failed_count}건"
        if details:
            message += f"\n\n실패 상세(최대 10건)\n{details}"
        QMessageBox.information(self, "CSV 결과", message)
        self.refresh_insurances()
        self.refresh_audit_logs()

    def _on_customer_row_selected(self, row: int, _column: int) -> None:
        item = self.customers_table.item(row, 0)
        if item is None:
            return

        selected_id = item.text()
        self.customer_id_input.setText(selected_id)
        self.insurance_customer_id_input.setText(selected_id)
        self._sync_customer_selector_by_id(selected_id)
        self.refresh_insurances()

    def _on_insurance_row_selected(self, row: int, _column: int) -> None:
        insurance_item = self.insurances_table.item(row, 0)
        customer_item = self.insurances_table.item(row, 1)
        if insurance_item is not None:
            self.insurance_id_input.setText(insurance_item.text())
        if customer_item is not None:
            self.insurance_customer_id_input.setText(customer_item.text())
            self._sync_customer_selector_by_id(customer_item.text())

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
        self.customer_id_input.clear()

    def clear_insurance_form(self, keep_customer_id: bool = False) -> None:
        self.insurance_id_input.clear()
        if not keep_customer_id:
            self.insurance_customer_id_input.clear()
            self.insurance_customer_selector.setCurrentIndex(0)
        self.contract_date_input.clear()
        self.contract_date_input.setText(date.today().isoformat())
        self.company_input.clear()
        self.policy_number_input.clear()
        self.product_name_input.clear()
        self.premium_input.clear()
        self.insured_person_input.clear()
        self.payment_day_input.clear()
        self.payment_day_input.setText("25")
        self.beneficiary_input.clear()

    def _render_customers(self, customers: list) -> None:
        self._render_customer_table(self.customers_table, customers)

    def _refresh_customer_selector(self, customers: list) -> None:
        current_id = self.insurance_customer_id_input.text().strip()
        self.insurance_customer_selector.blockSignals(True)
        self.insurance_customer_selector.clear()
        self.insurance_customer_selector.addItem("고객 선택", "")
        for customer in customers:
            self.insurance_customer_selector.addItem(
                f"{customer.id} - {customer.name}",
                str(customer.id),
            )
        self.insurance_customer_selector.blockSignals(False)
        if current_id:
            self._sync_customer_selector_by_id(current_id)

    def _on_customer_selector_changed(self, _index: int) -> None:
        customer_id = self.insurance_customer_selector.currentData()
        if customer_id:
            self.insurance_customer_id_input.setText(str(customer_id))

    def _sync_customer_selector_by_id(self, customer_id: str) -> None:
        for index in range(self.insurance_customer_selector.count()):
            if str(self.insurance_customer_selector.itemData(index)) == str(customer_id):
                self.insurance_customer_selector.setCurrentIndex(index)
                return

    def _render_insurances(self, insurances: list) -> None:
        self._render_insurance_table(self.insurances_table, insurances)

    def _render_audit_logs(self, logs: list) -> None:
        self._audit_rows = logs
        self._audit_details = []
        self.audit_table.setRowCount(len(logs))
        for row_index, log in enumerate(logs):
            detail = log.get("detail") or ""
            summary = detail.replace("\n", " ")
            if len(summary) > 120:
                summary = summary[:117] + "..."
            self._audit_details.append(detail)
            self.audit_table.setItem(row_index, 0, QTableWidgetItem(str(log.get("id", ""))))
            self.audit_table.setItem(row_index, 1, QTableWidgetItem(str(log.get("created_at", ""))))
            self.audit_table.setItem(row_index, 2, QTableWidgetItem(str(log.get("action", ""))))
            self.audit_table.setItem(row_index, 3, QTableWidgetItem(str(log.get("entity", ""))))
            self.audit_table.setItem(row_index, 4, QTableWidgetItem(str(log.get("entity_id", ""))))
            self.audit_table.setItem(row_index, 5, QTableWidgetItem(summary))
        if not logs:
            self.audit_detail_view.setPlainText("")

    def export_audit_logs_csv(self) -> None:
        if not self._audit_rows:
            QMessageBox.information(self, "안내", "내보낼 이력 데이터가 없습니다.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "이력 CSV 저장",
            "audit_logs.csv",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["id", "created_at", "action", "entity", "entity_id", "detail"])
                for row in self._audit_rows:
                    writer.writerow(
                        [
                            row.get("id", ""),
                            row.get("created_at", ""),
                            row.get("action", ""),
                            row.get("entity", ""),
                            row.get("entity_id", ""),
                            row.get("detail", ""),
                        ]
                    )
            QMessageBox.information(self, "완료", f"이력 CSV 저장 완료: {file_path}")
        except Exception as error:  # pylint: disable=broad-except
            QMessageBox.critical(self, "저장 오류", str(error))

    def _on_audit_row_selected(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._audit_details):
            self.audit_detail_view.setPlainText(self._audit_details[row])

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
