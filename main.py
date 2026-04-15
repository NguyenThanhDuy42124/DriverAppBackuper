"""Entry point for Driver/App backup and restore GUI."""

from __future__ import annotations

import sys
from pathlib import Path

import ctypes

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.admin import check_admin, request_admin
from ui.main_window import MainWindow


def _runtime_base_path() -> Path:
    """Return runtime base path for source and PyInstaller onefile mode."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


def _set_windows_app_id() -> None:
    """Set explicit Windows AppUserModelID so taskbar icon is consistent."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "DriverBackupWin.Desktop.App"
        )
    except Exception:
        # Ignore if unsupported on current Windows runtime.
        pass


def main() -> int:
    """Start the PyQt application."""
    if not check_admin():
        if request_admin():
            return 0

    _set_windows_app_id()
    app = QApplication(sys.argv)
    root_path = Path(__file__).resolve().parent
    icon_path = _runtime_base_path() / "easy-installation.ico"
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            app.setWindowIcon(icon)
    window = MainWindow(root_path)
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
