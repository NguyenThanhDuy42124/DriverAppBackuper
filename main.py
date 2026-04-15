"""Entry point for Driver/App backup and restore GUI."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.admin import check_admin, request_admin
from ui.main_window import MainWindow


def main() -> int:
    """Start the PyQt application."""
    if not check_admin():
        if request_admin():
            return 0

    app = QApplication(sys.argv)
    root_path = Path(__file__).resolve().parent
    icon_path = root_path / "easy-installation.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow(root_path)
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
