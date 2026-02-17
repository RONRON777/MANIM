"""Background worker tasks used by the main GUI window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Signal

if TYPE_CHECKING:
    from manim_app.repositories.audit_repository import AuditRepository
    from manim_app.services.csv_import_service import CsvImportService
    from manim_app.services.customer_service import CustomerService
    from manim_app.services.insurance_service import InsuranceService


class LoadSignals(QObject):
    """Signals for background loading tasks."""

    done = Signal(list)
    error = Signal(str)


class ImportSignals(QObject):
    """Signals for background CSV import tasks."""

    done = Signal(int, int, str)
    error = Signal(str)


class LoadCustomersTask(QRunnable):
    """Load customer list without blocking the UI thread."""

    def __init__(self, customer_service: CustomerService, limit: int, offset: int):
        super().__init__()
        self.customer_service = customer_service
        self.limit = limit
        self.offset = offset
        self.signals = LoadSignals()

    def run(self) -> None:
        try:
            customers = self.customer_service.list_customers(
                limit=self.limit,
                offset=self.offset,
            )
            self.signals.done.emit(customers)
        except Exception as error:  # pylint: disable=broad-except
            # Worker boundary: convert any failure to a user-visible message.
            self.signals.error.emit(str(error))


class LoadInsurancesTask(QRunnable):
    """Load insurance list without blocking the UI thread."""

    def __init__(
        self,
        insurance_service: InsuranceService,
        customer_id: int,
        limit: int,
        offset: int,
    ):
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
            # Worker boundary: convert any failure to a user-visible message.
            self.signals.error.emit(str(error))


class ImportCustomersCsvTask(QRunnable):
    """Import customer CSV in a background worker."""

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
            # Worker boundary: convert any failure to a user-visible message.
            self.signals.error.emit(str(error))


class ImportInsurancesCsvTask(QRunnable):
    """Import insurance CSV in a background worker."""

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
            # Worker boundary: convert any failure to a user-visible message.
            self.signals.error.emit(str(error))


class LoadAuditLogsTask(QRunnable):
    """Load audit logs in a background worker."""

    def __init__(
        self,
        audit_repo: AuditRepository,
        limit: int,
        action: str | None,
        entity: str | None,
        keyword: str | None,
        date_from: str | None,
        date_to: str | None,
    ):
        super().__init__()
        self.audit_repo = audit_repo
        self.limit = limit
        self.action = action
        self.entity = entity
        self.keyword = keyword
        self.date_from = date_from
        self.date_to = date_to
        self.signals = LoadSignals()

    def run(self) -> None:
        try:
            logs = self.audit_repo.list_logs(
                limit=self.limit,
                action=self.action,
                entity=self.entity,
                keyword=self.keyword,
                date_from=self.date_from,
                date_to=self.date_to,
            )
            self.signals.done.emit(logs)
        except Exception as error:  # pylint: disable=broad-except
            # Worker boundary: convert any failure to a user-visible message.
            self.signals.error.emit(str(error))
