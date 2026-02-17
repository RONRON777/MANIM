"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from manim_app.core.container import build_container
from manim_app.ui.main_window import MainWindow


def run() -> None:
    """Launch the GUI application."""
    container = build_container()
    removed = container.audit_repo.cleanup_old_logs(container.config.logging.retention_days)
    if removed:
        print(f"Cleaned old logs: {removed}")

    app = QApplication(sys.argv)
    window = MainWindow(
        container.customer_service,
        container.insurance_service,
        container.csv_import_service,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
