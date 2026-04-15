"""Main PyQt6 window for driver and application backup/restore."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Callable, Dict, List

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QProgressBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.admin import check_admin
from core.backup import backup_selected_drivers, full_backup_system, quick_backup
from core.driver_loader import filter_drivers, get_driver_list, search_driver
from core.restore import restore_from_folder
from core.winget_manager import (
    default_backup_path,
    export_restore_script,
    export_selected_apps_to_file,
    filter_apps_by_source,
    get_installed_apps,
    import_apps_from_file,
    install_multiple_apps,
    search_app,
)
from utils.file_utils import export_config, import_config, load_json_file, open_folder
from utils.lang import change_language, load_language, translate
from utils.logger import AppLogger

DriverInfo = Dict[str, str]
AppInfo = Dict[str, str]


class Worker(QObject):
    """Generic worker to run long tasks in a background thread."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, fn: Callable[..., Any], kwargs: Dict[str, Any]) -> None:
        super().__init__()
        self._fn = fn
        self._kwargs = kwargs

    def run(self) -> None:
        """Execute the task and emit result, progress, or errors."""
        try:
            signature = inspect.signature(self._fn)
            kwargs = dict(self._kwargs)
            if "progress_callback" in signature.parameters:
                kwargs["progress_callback"] = self._emit_progress
            result = self._fn(**kwargs)
            self.finished.emit(result)
        except Exception as error:  # pylint: disable=broad-except
            self.error.emit(str(error))

    def _emit_progress(self, percent: int, message: str) -> None:
        """Emit progress signal from worker."""
        self.progress.emit(percent, message)


class MainWindow(QMainWindow):
    """Main application window with Drivers and Applications tabs."""

    def __init__(self, root_path: Path) -> None:
        super().__init__()
        self.root_path = root_path
        self.settings_path = root_path / "config" / "settings.json"
        self.lang_path = root_path / "lang" / "lang.json"

        self.settings = load_json_file(str(self.settings_path))
        self.language_data = load_language(str(self.lang_path))
        self.language_code = self.settings.get("default_language", "vi")
        self.theme_mode = self.settings.get("theme_mode", "black")

        log_file = self.settings.get("log_file", "driver_backup.log")
        self.logger = AppLogger(str(root_path / log_file), self.settings.get("debug_mode", False))
        self.logger.set_gui_sink(self._append_log)

        self.drivers: List[DriverInfo] = []
        self.filtered_drivers: List[DriverInfo] = []
        self.apps: List[AppInfo] = []
        self.filtered_apps: List[AppInfo] = []
        self.threads: List[QThread] = []
        self.workers: List[Worker] = []
        self.is_loading_drivers = False
        self.is_loading_apps = False
        self.last_backup_folder = self.settings.get("last_backup_folder", "")

        self._build_ui()
        self._set_button_roles()
        self._apply_modern_style()
        self._bind_events()
        self._apply_language()
        self._set_admin_status()
        QTimer.singleShot(0, self._sync_all_column_widths)

    def _set_button_roles(self) -> None:
        """Assign semantic roles for button color styling."""
        self.button_load_drivers.setProperty("role", "load")
        self.button_load_apps.setProperty("role", "load")

        self.button_backup_selected_drivers.setProperty("role", "backup")
        self.button_quick_backup_drivers.setProperty("role", "backup")
        self.button_backup_selected_apps.setProperty("role", "backup")
        self.button_full_backup.setProperty("role", "backup")

        self.button_restore_drivers.setProperty("role", "restore")
        self.button_restore_apps.setProperty("role", "restore")
        self.button_restore_all_apps.setProperty("role", "restore")

        self.button_export_driver_csv.setProperty("role", "export")
        self.button_export_restore_script.setProperty("role", "export")
        self.button_export_config.setProperty("role", "export")

        self.button_import_app_backup.setProperty("role", "import")
        self.button_import_config.setProperty("role", "import")

        self.button_select_all_drivers.setProperty("role", "neutral")
        self.button_unselect_all_drivers.setProperty("role", "neutral")
        self.button_select_all_apps.setProperty("role", "neutral")
        self.button_unselect_all_apps.setProperty("role", "neutral")
        self.button_open_backup_folder.setProperty("role", "neutral")

    def _apply_modern_style(self) -> None:
        """Apply active theme stylesheet."""
        dark = self.theme_mode == "black"
        if dark:
            bg_main = "#0D1420"
            bg_panel = "#152235"
            bg_panel_soft = "#1B2B41"
            border = "#29415F"
            text = "#E9F1FF"
            text_soft = "#9EB4D1"
            tab_bg = "#1C2D44"
            disabled_bg = "#24364F"
            disabled_text = "#7D93B0"
            progress = "#25D0A0"

            load_btn = "#2483FF"
            load_border = "#1D6DDA"

            backup_btn = "#10B981"
            backup_border = "#0D9468"

            restore_btn = "#E09A2C"
            restore_border = "#C6841E"

            export_btn = "#4F7DF0"
            export_border = "#3E68D2"

            import_btn = "#6e6256"
            import_border = "#5d5348"
            neutral_btn = "#3A5477"
            neutral_border = "#2F4663"
            hover_border = "#7CC1FF"
            row_alt = "rgba(124, 193, 255, 0.08)"
            focus_ring = "#8BD2FF"
        else:
            bg_main = "#F5F1E8"
            bg_panel = "#FFF9F0"
            bg_panel_soft = "#F9F0E1"
            border = "#D9C8AD"
            text = "#1E2C42"
            text_soft = "#6D7F99"
            tab_bg = "#EBDECA"
            disabled_bg = "#EFE4D3"
            disabled_text = "#8C7D67"
            progress = "#0B52D4"

            load_btn = "#0B56E0"
            load_border = "#0848BC"

            backup_btn = "#0EA473"
            backup_border = "#0B875F"

            restore_btn = "#D87922"
            restore_border = "#B8641B"

            export_btn = "#3D66D4"
            export_border = "#3155B5"

            import_btn = "#E8D7C4"
            import_border = "#D3BFA8"

            neutral_btn = "#F0E0CE"
            neutral_border = "#DDC8B2"
            hover_border = "#0B56E0"
            row_alt = "rgba(11, 86, 224, 0.06)"
            focus_ring = "#2F6FE6"

        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background-color: {bg_main};
                color: {text};
                font-size: 13px;
                font-family: "Segoe UI Variable", "Bahnschrift", "Segoe UI";
            }}

            QGroupBox {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 12px;
                margin-top: 12px;
                padding: 10px;
                font-weight: 600;
            }}

            QLineEdit, QComboBox, QTableWidget, QTextEdit {{
                background-color: {bg_panel_soft};
                border: 1px solid {border};
                border-radius: 9px;
                padding: 7px;
                color: {text};
                selection-background-color: {load_btn};
                selection-color: #ffffff;
            }}

            QLineEdit:focus, QComboBox:focus, QTableWidget:focus, QTextEdit:focus {{
                border: 1px solid {focus_ring};
            }}

            QTabWidget::pane {{
                border: 1px solid {border};
                border-radius: 10px;
                top: -1px;
                background: {bg_panel};
            }}

            QTabBar::tab {{
                background: {tab_bg};
                border: 1px solid {border};
                padding: 8px 14px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                color: {text_soft};
                min-height: 20px;
            }}

            QTabBar::tab:selected {{
                color: {text};
                font-weight: 700;
                background: {bg_panel};
                border-bottom-color: {bg_panel};
            }}

            QPushButton {{
                border-radius: 9px;
                padding: 7px 12px;
                color: #f7fbff;
                border: 1px solid transparent;
                font-weight: 600;
                min-height: 20px;
            }}

            QPushButton[role="load"] {{ background-color: {load_btn}; border-color: {load_border}; }}
            QPushButton[role="backup"] {{ background-color: {backup_btn}; border-color: {backup_border}; }}
            QPushButton[role="restore"] {{ background-color: {restore_btn}; border-color: {restore_border}; }}
            QPushButton[role="export"] {{ background-color: {export_btn}; border-color: {export_border}; }}

            QPushButton[role="import"] {{
                background-color: {import_btn};
                border-color: {import_border};
                color: {text};
            }}

            QPushButton[role="neutral"] {{
                background-color: {neutral_btn};
                border-color: {neutral_border};
                color: {text};
            }}

            QPushButton:hover {{
                border-color: {hover_border};
            }}

            QPushButton:pressed {{
                padding-top: 8px;
                padding-bottom: 6px;
            }}

            QPushButton:disabled {{
                color: {disabled_text};
                background-color: {disabled_bg};
                border-color: {border};
            }}

            QHeaderView::section {{
                background-color: {tab_bg};
                color: {text};
                border: 0;
                border-bottom: 1px solid {border};
                padding: 7px;
                font-weight: 700;
            }}

            QTableWidget {{
                gridline-color: {border};
                alternate-background-color: {row_alt};
            }}

            QTableWidget::item:selected {{
                background-color: rgba(36, 131, 255, 0.20);
                color: {text};
            }}

            QProgressBar {{
                border: 1px solid {border};
                border-radius: 8px;
                background: {bg_panel_soft};
                text-align: center;
                color: {text};
                min-height: 14px;
            }}

            QProgressBar::chunk {{
                background-color: {progress};
                border-radius: 7px;
            }}
            """
        )

        self.table_drivers.setAlternatingRowColors(True)
        self.table_apps.setAlternatingRowColors(True)
        self.table_drivers.setShowGrid(False)
        self.table_apps.setShowGrid(False)

    def _build_ui(self) -> None:
        """Build all widgets and layouts."""
        central_widget = QWidget()
        root_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()
        self.label_language = QLabel()
        self.combo_language = QComboBox()
        self.combo_language.addItem("VI", "vi")
        self.combo_language.addItem("EN", "en")

        self.label_mode = QLabel()
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("", "full")
        self.combo_mode.addItem("", "strict")

        self.label_theme = QLabel()
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("", "black")
        self.combo_theme.addItem("", "white")

        self.button_full_backup = QPushButton()
        self.button_export_config = QPushButton()
        self.button_import_config = QPushButton()

        top_layout.addWidget(self.label_language)
        top_layout.addWidget(self.combo_language)
        top_layout.addWidget(self.label_mode)
        top_layout.addWidget(self.combo_mode)
        top_layout.addWidget(self.label_theme)
        top_layout.addWidget(self.combo_theme)
        top_layout.addWidget(self.button_full_backup)
        top_layout.addWidget(self.button_export_config)
        top_layout.addWidget(self.button_import_config)
        top_layout.addStretch()

        self.tab_widget = QTabWidget()
        self.driver_tab = self._build_driver_tab()
        self.app_tab = self._build_application_tab()
        self.tab_widget.addTab(self.driver_tab, "")
        self.tab_widget.addTab(self.app_tab, "")

        root_layout.addLayout(top_layout)
        root_layout.addWidget(self.tab_widget)

        self.setCentralWidget(central_widget)
        self.resize(1200, 760)

    def _build_driver_tab(self) -> QWidget:
        """Create the Drivers tab widgets."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        filter_group = QGroupBox()
        filter_layout = QGridLayout(filter_group)
        self.label_driver_search = QLabel()
        self.input_driver_search = QLineEdit()
        self.label_driver_filter = QLabel()
        self.combo_driver_filter = QComboBox()
        self.combo_driver_filter.addItem("", "all")
        self.combo_driver_filter.addItem("", "running")
        self.combo_driver_filter.addItem("", "stopped")

        filter_layout.addWidget(self.label_driver_search, 0, 0)
        filter_layout.addWidget(self.input_driver_search, 0, 1)
        filter_layout.addWidget(self.label_driver_filter, 0, 2)
        filter_layout.addWidget(self.combo_driver_filter, 0, 3)

        self.table_drivers = QTableWidget(0, 4)
        self.table_drivers.setAlternatingRowColors(True)
        driver_header = self.table_drivers.horizontalHeader()
        driver_header.setStretchLastSection(False)
        driver_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        driver_header.setMinimumSectionSize(24)

        buttons_layout = QHBoxLayout()
        self.button_load_drivers = QPushButton()
        self.button_select_all_drivers = QPushButton()
        self.button_unselect_all_drivers = QPushButton()
        self.button_backup_selected_drivers = QPushButton()
        self.button_quick_backup_drivers = QPushButton()
        self.button_restore_drivers = QPushButton()
        self.button_export_driver_csv = QPushButton()
        self.button_open_backup_folder = QPushButton()

        for widget in [
            self.button_load_drivers,
            self.button_select_all_drivers,
            self.button_unselect_all_drivers,
            self.button_backup_selected_drivers,
            self.button_quick_backup_drivers,
            self.button_restore_drivers,
            self.button_export_driver_csv,
            self.button_open_backup_folder,
        ]:
            buttons_layout.addWidget(widget)

        self.label_driver_selected_count = QLabel()
        self.progress_drivers = QProgressBar()
        self.log_drivers = QTextEdit()
        self.log_drivers.setReadOnly(True)

        layout.addWidget(filter_group)
        layout.addWidget(self.table_drivers)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.label_driver_selected_count)
        layout.addWidget(self.progress_drivers)
        layout.addWidget(self.log_drivers)
        return tab

    def _build_application_tab(self) -> QWidget:
        """Create the Applications tab widgets."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        filter_group = QGroupBox()
        filter_layout = QGridLayout(filter_group)
        self.label_app_search = QLabel()
        self.input_app_search = QLineEdit()
        self.label_app_filter = QLabel()
        self.combo_app_filter = QComboBox()
        self.combo_app_filter.addItem("", "all")
        self.combo_app_filter.addItem("Winget", "winget")
        self.combo_app_filter.addItem("MSStore", "msstore")

        filter_layout.addWidget(self.label_app_search, 0, 0)
        filter_layout.addWidget(self.input_app_search, 0, 1)
        filter_layout.addWidget(self.label_app_filter, 0, 2)
        filter_layout.addWidget(self.combo_app_filter, 0, 3)

        self.table_apps = QTableWidget(0, 6)
        self.table_apps.setAlternatingRowColors(True)
        app_header = self.table_apps.horizontalHeader()
        app_header.setStretchLastSection(False)
        app_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        app_header.setMinimumSectionSize(24)

        buttons_layout = QHBoxLayout()
        self.button_load_apps = QPushButton()
        self.button_select_all_apps = QPushButton()
        self.button_unselect_all_apps = QPushButton()
        self.button_backup_selected_apps = QPushButton()
        self.button_import_app_backup = QPushButton()
        self.button_restore_apps = QPushButton()
        self.button_restore_all_apps = QPushButton()
        self.button_export_restore_script = QPushButton()

        for widget in [
            self.button_load_apps,
            self.button_select_all_apps,
            self.button_unselect_all_apps,
            self.button_backup_selected_apps,
            self.button_import_app_backup,
            self.button_restore_apps,
            self.button_restore_all_apps,
            self.button_export_restore_script,
        ]:
            buttons_layout.addWidget(widget)

        self.label_app_selected_count = QLabel()
        self.progress_apps = QProgressBar()
        self.log_apps = QTextEdit()
        self.log_apps.setReadOnly(True)

        layout.addWidget(filter_group)
        layout.addWidget(self.table_apps)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.label_app_selected_count)
        layout.addWidget(self.progress_apps)
        layout.addWidget(self.log_apps)
        return tab

    def _bind_events(self) -> None:
        """Bind UI events to handlers."""
        self.combo_language.currentIndexChanged.connect(self._on_language_changed)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self.button_load_drivers.clicked.connect(self._load_drivers)
        self.button_select_all_drivers.clicked.connect(lambda: self._toggle_select_all(self.table_drivers, True))
        self.button_unselect_all_drivers.clicked.connect(lambda: self._toggle_select_all(self.table_drivers, False))
        self.button_backup_selected_drivers.clicked.connect(self._backup_selected_drivers)
        self.button_quick_backup_drivers.clicked.connect(self._quick_backup_drivers)
        self.button_restore_drivers.clicked.connect(self._restore_drivers)
        self.button_export_driver_csv.clicked.connect(self._export_driver_csv)
        self.button_open_backup_folder.clicked.connect(self._open_backup_folder)
        self.button_full_backup.clicked.connect(self._full_backup_system)

        self.input_driver_search.textChanged.connect(self._refresh_driver_table)
        self.combo_driver_filter.currentIndexChanged.connect(self._refresh_driver_table)
        self.table_drivers.itemChanged.connect(self._update_selected_counts)

        self.button_load_apps.clicked.connect(self._load_apps)
        self.button_select_all_apps.clicked.connect(lambda: self._toggle_select_all(self.table_apps, True))
        self.button_unselect_all_apps.clicked.connect(lambda: self._toggle_select_all(self.table_apps, False))
        self.button_backup_selected_apps.clicked.connect(self._backup_selected_apps)
        self.button_import_app_backup.clicked.connect(self._import_app_backup)
        self.button_restore_apps.clicked.connect(self._restore_selected_apps)
        self.button_restore_all_apps.clicked.connect(self._quick_restore_all_apps)
        self.button_export_restore_script.clicked.connect(self._export_restore_script)

        self.input_app_search.textChanged.connect(self._refresh_app_table)
        self.combo_app_filter.currentIndexChanged.connect(self._refresh_app_table)
        self.table_apps.itemChanged.connect(self._update_selected_counts)

        self.button_export_config.clicked.connect(self._export_config)
        self.button_import_config.clicked.connect(self._import_config)

    def _tr(self, key: str, **kwargs: Any) -> str:
        """Translate a UI key with active language."""
        return translate(self.language_data, key, self.language_code, **kwargs)

    def _apply_language(self) -> None:
        """Apply translated text to all visible widgets."""
        self.setWindowTitle(self._tr("app_title"))
        self.label_language.setText(self._tr("language"))
        self.label_mode.setText(self._tr("mode"))
        self.label_theme.setText(self._tr("theme"))

        self.combo_mode.setItemText(0, self._tr("mode_full"))
        self.combo_mode.setItemText(1, self._tr("mode_strict"))
        self.combo_theme.setItemText(0, self._tr("theme_black"))
        self.combo_theme.setItemText(1, self._tr("theme_white"))

        self.tab_widget.setTabText(0, self._tr("drivers_tab"))
        self.tab_widget.setTabText(1, self._tr("applications_tab"))

        self.label_driver_search.setText(self._tr("search"))
        self.label_driver_filter.setText(self._tr("filter"))
        self.combo_driver_filter.setItemText(0, self._tr("filter_all"))
        self.combo_driver_filter.setItemText(1, self._tr("filter_running"))
        self.combo_driver_filter.setItemText(2, self._tr("filter_stopped"))

        self.table_drivers.setHorizontalHeaderLabels(
            [self._tr("select"), self._tr("device_name"), self._tr("inf_name"), self._tr("status")]
        )

        self.button_load_drivers.setText(self._tr("load_drivers"))
        self.button_select_all_drivers.setText(self._tr("select_all"))
        self.button_unselect_all_drivers.setText(self._tr("unselect_all"))
        self.button_backup_selected_drivers.setText(self._tr("backup_selected"))
        self.button_quick_backup_drivers.setText(self._tr("quick_backup"))
        self.button_restore_drivers.setText(self._tr("restore"))
        self.button_export_driver_csv.setText(self._tr("export_csv"))
        self.button_open_backup_folder.setText(self._tr("open_backup_folder"))
        self.button_full_backup.setText(self._tr("full_backup_system"))

        self.label_app_search.setText(self._tr("search"))
        self.label_app_filter.setText(self._tr("filter"))
        self.combo_app_filter.setItemText(0, self._tr("filter_all"))
        self.table_apps.setHorizontalHeaderLabels(
            [
                self._tr("select"),
                self._tr("app_name"),
                self._tr("app_id"),
                self._tr("app_version"),
                self._tr("app_source"),
                self._tr("app_status"),
            ]
        )

        self.button_load_apps.setText(self._tr("load_apps"))
        self.button_select_all_apps.setText(self._tr("select_all"))
        self.button_unselect_all_apps.setText(self._tr("unselect_all"))
        self.button_backup_selected_apps.setText(self._tr("backup_selected_apps"))
        self.button_import_app_backup.setText(self._tr("import_backup_file"))
        self.button_restore_apps.setText(self._tr("restore_apps"))
        self.button_restore_all_apps.setText(self._tr("quick_restore_all_apps"))
        self.button_export_restore_script.setText(self._tr("export_restore_script"))

        self.button_export_config.setText(self._tr("export_config"))
        self.button_import_config.setText(self._tr("import_config"))

        self._apply_button_tooltips()

        self.combo_language.blockSignals(True)
        lang_index = self.combo_language.findData(self.language_code)
        if lang_index >= 0:
            self.combo_language.setCurrentIndex(lang_index)
        self.combo_language.blockSignals(False)

        self.combo_mode.blockSignals(True)
        mode_index = self.combo_mode.findData(self.settings.get("default_backup_mode", "full"))
        if mode_index >= 0:
            self.combo_mode.setCurrentIndex(mode_index)
        self.combo_mode.blockSignals(False)

        self.combo_theme.blockSignals(True)
        theme_index = self.combo_theme.findData(self.theme_mode)
        if theme_index >= 0:
            self.combo_theme.setCurrentIndex(theme_index)
        self.combo_theme.blockSignals(False)

        self._sync_all_column_widths()
        self._update_selected_counts()

    def _apply_button_tooltips(self) -> None:
        """Apply translated tooltips for button actions."""
        self.button_load_drivers.setToolTip(self._tr("tip_load_drivers"))
        self.button_backup_selected_drivers.setToolTip(self._tr("tip_backup_selected_drivers"))
        self.button_restore_drivers.setToolTip(self._tr("tip_restore_drivers"))
        self.button_export_driver_csv.setToolTip(self._tr("tip_export_driver_csv"))
        self.button_open_backup_folder.setToolTip(self._tr("tip_open_backup_folder"))
        self.button_full_backup.setToolTip(self._tr("tip_full_backup"))

        self.button_load_apps.setToolTip(self._tr("tip_load_apps"))
        self.button_backup_selected_apps.setToolTip(self._tr("tip_backup_selected_apps"))
        self.button_import_app_backup.setToolTip(self._tr("tip_import_app_backup"))
        self.button_restore_apps.setToolTip(self._tr("tip_restore_apps"))
        self.button_restore_all_apps.setToolTip(self._tr("tip_restore_all_apps"))
        self.button_export_restore_script.setToolTip(self._tr("tip_export_restore_script"))

        self.button_export_config.setToolTip(self._tr("tip_export_config"))
        self.button_import_config.setToolTip(self._tr("tip_import_config"))

    def _set_admin_status(self) -> None:
        """Display warning when app is not running as admin."""
        if not check_admin():
            self._append_log(self._tr("admin_required"))

    def _start_worker(
        self,
        fn: Callable[..., Any],
        kwargs: Dict[str, Any],
        progress_bar: QProgressBar,
        on_finished: Callable[[Any], None],
    ) -> None:
        """Run task in a QThread and connect lifecycle handlers."""
        thread = QThread()
        worker = Worker(fn, kwargs)
        worker.moveToThread(thread)
        self.workers.append(worker)

        thread.started.connect(worker.run)
        worker.progress.connect(lambda value, message: self._on_progress(progress_bar, value, message))
        worker.finished.connect(on_finished)
        worker.error.connect(self._on_error)

        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread, worker))

        self.threads.append(thread)
        progress_bar.setValue(0)
        thread.start()

    def _cleanup_thread(self, thread: QThread, worker: Worker) -> None:
        """Remove finished thread/worker from tracking lists."""
        if thread in self.threads:
            self.threads.remove(thread)
        if worker in self.workers:
            self.workers.remove(worker)

    def _on_progress(self, progress_bar: QProgressBar, value: int, message: str) -> None:
        """Update progress bar and append log message."""
        progress_bar.setValue(value)
        self._append_log(message)

    def _append_log(self, message: str) -> None:
        """Append logs to both tab log widgets."""
        self.log_drivers.append(message)
        self.log_apps.append(message)

    def _refresh_driver_table(self) -> None:
        """Apply filter/search and re-render driver table."""
        filtered = filter_drivers(self.drivers, self.combo_driver_filter.currentData())
        self.filtered_drivers = search_driver(filtered, self.input_driver_search.text())
        self._render_driver_table(self.filtered_drivers)

    def _render_driver_table(self, drivers: List[DriverInfo]) -> None:
        """Render drivers into table with checkbox items."""
        self.table_drivers.blockSignals(True)
        self.table_drivers.setRowCount(len(drivers))

        for row, driver in enumerate(drivers):
            select_item = QTableWidgetItem()
            select_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            select_item.setCheckState(Qt.CheckState.Unchecked)
            select_item.setData(Qt.ItemDataRole.UserRole, driver)

            self.table_drivers.setItem(row, 0, select_item)
            self.table_drivers.setItem(row, 1, QTableWidgetItem(driver.get("device_name", "")))
            self.table_drivers.setItem(row, 2, QTableWidgetItem(driver.get("inf_name", "")))
            self.table_drivers.setItem(row, 3, QTableWidgetItem(driver.get("status", "")))

        self.table_drivers.blockSignals(False)
        self._apply_driver_column_widths()
        self._update_selected_counts()

    def _apply_driver_column_widths(self) -> None:
        """Apply driver table column widths by percentage."""
        self._apply_column_widths(self.table_drivers, [10, 40, 30, 20])

    def _load_drivers(self) -> None:
        """Load drivers in background and refresh table."""
        if self.is_loading_drivers:
            self.logger.log_info(self._tr("already_loading"))
            return
        self.is_loading_drivers = True
        self.button_load_drivers.setEnabled(False)
        self._start_worker(get_driver_list, {}, self.progress_drivers, self._on_drivers_loaded)

    def _on_drivers_loaded(self, drivers: Any) -> None:
        """Apply loaded drivers and update UI."""
        self.is_loading_drivers = False
        self.button_load_drivers.setEnabled(True)
        self.drivers = list(drivers)
        self._refresh_driver_table()
        self.logger.log_info(self._tr("load_done", count=len(self.drivers)))

    def _get_selected_from_table(self, table: QTableWidget) -> List[Dict[str, str]]:
        """Return selected row payload objects from a checkbox table."""
        selected: List[Dict[str, str]] = []
        for row in range(table.rowCount()):
            select_item = table.item(row, 0)
            if select_item and select_item.checkState() == Qt.CheckState.Checked:
                payload = select_item.data(Qt.ItemDataRole.UserRole)
                if payload:
                    selected.append(payload)
        return selected

    def _toggle_select_all(self, table: QTableWidget, checked: bool) -> None:
        """Select or unselect all rows in a checkbox table."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        table.blockSignals(True)
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                item.setCheckState(state)
        table.blockSignals(False)
        self._update_selected_counts()

    def _update_selected_counts(self) -> None:
        """Update selected-count labels for both tabs."""
        driver_count = len(self._get_selected_from_table(self.table_drivers))
        app_count = len(self._get_selected_from_table(self.table_apps))
        self.label_driver_selected_count.setText(self._tr("selected_count", count=driver_count))
        self.label_app_selected_count.setText(self._tr("selected_count", count=app_count))

    def _choose_folder(self, title_key: str) -> str:
        """Open folder picker and return selected directory."""
        return QFileDialog.getExistingDirectory(self, self._tr(title_key), str(self.root_path))

    def _backup_selected_drivers(self) -> None:
        """Backup checked drivers with selected mode."""
        selected = self._get_selected_from_table(self.table_drivers)
        if not selected:
            QMessageBox.information(self, self._tr("info"), self._tr("no_driver_selected"))
            return

        folder = self._choose_folder("choose_backup_folder")
        if not folder:
            return

        self.last_backup_folder = folder
        mode = self.combo_mode.currentData()
        kwargs = {"selected_drivers": selected, "output_folder": folder, "mode": mode}
        self._start_worker(backup_selected_drivers, kwargs, self.progress_drivers, self._on_driver_backup_done)

    def _quick_backup_drivers(self) -> None:
        """Run strict quick backup for selected drivers."""
        selected = self._get_selected_from_table(self.table_drivers)
        if not selected:
            QMessageBox.information(self, self._tr("info"), self._tr("no_driver_selected"))
            return

        folder = self._choose_folder("choose_backup_folder")
        if not folder:
            return

        self.last_backup_folder = folder
        kwargs = {"selected_drivers": selected, "output_folder": folder}
        self._start_worker(quick_backup, kwargs, self.progress_drivers, self._on_driver_backup_done)

    def _on_driver_backup_done(self, summary: Any) -> None:
        """Display driver backup summary."""
        self.logger.log_info(f"{self._tr('backup_done')}: {summary}")
        QMessageBox.information(self, self._tr("success"), f"{self._tr('backup_done')}: {summary}")

    def _restore_drivers(self) -> None:
        """Restore drivers from a selected folder."""
        folder = self._choose_folder("choose_restore_folder")
        if not folder:
            return
        self._start_worker(restore_from_folder, {"folder_path": folder}, self.progress_drivers, self._on_restore_done)

    def _on_restore_done(self, summary: Any) -> None:
        """Display restore summary."""
        self.logger.log_info(f"{self._tr('restore_done')}: {summary}")
        QMessageBox.information(self, self._tr("success"), f"{self._tr('restore_done')}: {summary}")

    def _export_driver_csv(self) -> None:
        """Export visible drivers to CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("choose_export_csv"),
            str(self.root_path / "drivers.csv"),
            "CSV (*.csv)",
        )
        if not file_path:
            return

        import csv

        with open(file_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["device_name", "inf_name", "status"])
            writer.writeheader()
            for driver in self.filtered_drivers:
                writer.writerow(driver)

        self.logger.log_info(self._tr("csv_exported"))

    def _open_backup_folder(self) -> None:
        """Open last backup folder if available."""
        if not self.last_backup_folder:
            QMessageBox.information(self, self._tr("info"), self._tr("no_backup_folder"))
            return

        open_folder(self.last_backup_folder)

    def _refresh_app_table(self) -> None:
        """Apply app filter/search and render table."""
        filtered = filter_apps_by_source(self.apps, self.combo_app_filter.currentData())
        self.filtered_apps = search_app(filtered, self.input_app_search.text())
        self._render_app_table(self.filtered_apps)

    def _render_app_table(self, apps: List[AppInfo]) -> None:
        """Render apps into table with checkbox items."""
        self.table_apps.blockSignals(True)
        self.table_apps.setRowCount(len(apps))

        for row, app in enumerate(apps):
            select_item = QTableWidgetItem()
            select_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            select_item.setCheckState(Qt.CheckState.Unchecked)
            select_item.setData(Qt.ItemDataRole.UserRole, app)

            self.table_apps.setItem(row, 0, select_item)
            self.table_apps.setItem(row, 1, QTableWidgetItem(app.get("name", "")))
            self.table_apps.setItem(row, 2, QTableWidgetItem(app.get("id", "")))
            self.table_apps.setItem(row, 3, QTableWidgetItem(app.get("version", "")))
            self.table_apps.setItem(row, 4, QTableWidgetItem(app.get("source", "")))
            self.table_apps.setItem(row, 5, QTableWidgetItem(app.get("status", "Not installed")))

        self.table_apps.blockSignals(False)
        self._apply_app_column_widths()
        self._update_selected_counts()

    def _apply_app_column_widths(self) -> None:
        """Apply app table column widths by percentage."""
        self._apply_column_widths(self.table_apps, [10, 40, 20, 10, 10, 10])

    def _apply_column_widths(self, table: QTableWidget, percentages: List[int]) -> None:
        """Apply exact percentage widths to table columns so total equals 100%."""
        if table.columnCount() != len(percentages):
            return

        total_width = max(1, table.viewport().width())
        widths: List[int] = []
        used = 0

        for percent in percentages[:-1]:
            width = int(total_width * percent / 100)
            widths.append(width)
            used += width

        widths.append(max(1, total_width - used))

        for index, width in enumerate(widths):
            table.setColumnWidth(index, width)

    def _sync_all_column_widths(self) -> None:
        """Synchronize percentage widths for all tables."""
        self._apply_driver_column_widths()
        self._apply_app_column_widths()

    def _load_apps(self) -> None:
        """Load installed apps from winget."""
        if self.is_loading_apps:
            self.logger.log_info(self._tr("already_loading"))
            return
        self.is_loading_apps = True
        self.button_load_apps.setEnabled(False)
        self._start_worker(get_installed_apps, {}, self.progress_apps, self._on_apps_loaded)

    def _on_apps_loaded(self, apps: Any) -> None:
        """Apply loaded apps and refresh list."""
        self.is_loading_apps = False
        self.button_load_apps.setEnabled(True)
        self.apps = list(apps)
        self._refresh_app_table()
        self.logger.log_info(self._tr("apps_load_done", count=len(self.apps)))

    def _backup_selected_apps(self) -> None:
        """Backup selected apps to JSON or CSV."""
        selected = self._get_selected_from_table(self.table_apps)
        if not selected:
            QMessageBox.information(self, self._tr("info"), self._tr("no_app_selected"))
            return

        default_path = default_backup_path(str(self.root_path))
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("choose_export_apps"),
            default_path,
            "JSON (*.json);;CSV (*.csv)",
        )
        if not file_path:
            return

        export_selected_apps_to_file(selected, file_path)
        self.logger.log_info(self._tr("apps_backup_done"))

    def _import_app_backup(self) -> None:
        """Import apps from a backup JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("import_backup_file"),
            str(self.root_path),
            "JSON (*.json)",
        )
        if not file_path:
            return

        self.apps = import_apps_from_file(file_path)
        self._refresh_app_table()
        self.logger.log_info(self._tr("apps_import_done"))

    def _restore_selected_apps(self) -> None:
        """Restore selected applications by winget install."""
        selected = self._get_selected_from_table(self.table_apps)
        if not selected:
            QMessageBox.information(self, self._tr("info"), self._tr("no_app_selected"))
            return

        kwargs = {"app_list": selected, "retries": 1, "skip_installed": True}
        self._start_worker(install_multiple_apps, kwargs, self.progress_apps, self._on_restore_apps_done)

    def _quick_restore_all_apps(self) -> None:
        """Restore all apps currently displayed."""
        if not self.filtered_apps:
            QMessageBox.information(self, self._tr("info"), self._tr("no_app_selected"))
            return

        kwargs = {"app_list": list(self.filtered_apps), "retries": 1, "skip_installed": True}
        self._start_worker(install_multiple_apps, kwargs, self.progress_apps, self._on_restore_apps_done)

    def _on_restore_apps_done(self, summary: Any) -> None:
        """Display application restore summary."""
        self._refresh_app_table()
        self.logger.log_info(f"{self._tr('restore_done')}: {summary}")
        QMessageBox.information(self, self._tr("success"), f"{self._tr('restore_done')}: {summary}")

    def _export_restore_script(self) -> None:
        """Export a .bat install script for selected apps."""
        selected = self._get_selected_from_table(self.table_apps)
        if not selected:
            QMessageBox.information(self, self._tr("info"), self._tr("no_app_selected"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("export_restore_script"),
            str(self.root_path / "restore_apps.bat"),
            "Batch (*.bat)",
        )
        if not file_path:
            return

        export_restore_script(selected, file_path)
        self.logger.log_info(self._tr("script_exported"))

    def _full_backup_system(self) -> None:
        """Backup selected drivers and selected apps in one action."""
        selected_drivers = self._get_selected_from_table(self.table_drivers)
        selected_apps = self._get_selected_from_table(self.table_apps)

        if not selected_drivers and not selected_apps:
            QMessageBox.information(self, self._tr("info"), self._tr("nothing_selected"))
            return

        folder = self._choose_folder("choose_backup_folder")
        if not folder:
            return

        def _app_backup(target_folder: Path) -> Dict[str, int]:
            backup_file = target_folder / default_backup_path(str(target_folder)).split("\\")[-1]
            export_selected_apps_to_file(selected_apps, str(backup_file))
            return {"total": len(selected_apps), "success": len(selected_apps), "failed": 0}

        kwargs = {
            "selected_drivers": selected_drivers,
            "output_folder": folder,
            "app_backup_callback": _app_backup,
        }
        self._start_worker(full_backup_system, kwargs, self.progress_drivers, self._on_full_backup_done)

    def _on_full_backup_done(self, result: Any) -> None:
        """Display full backup summary."""
        driver_summary, app_summary = result
        self.logger.log_info(f"Driver summary: {driver_summary}")
        if app_summary:
            self.logger.log_info(f"App summary: {app_summary}")
        QMessageBox.information(self, self._tr("success"), self._tr("full_backup_done"))

    def _export_config(self) -> None:
        """Export config settings to a user selected file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("choose_export_config"),
            str(self.root_path / "config_export.json"),
            "JSON (*.json)",
        )
        if not file_path:
            return

        export_config(self.settings, file_path)
        self.logger.log_info(self._tr("config_exported"))

    def _import_config(self) -> None:
        """Import config settings from JSON file and refresh UI language."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("choose_import_config"),
            str(self.root_path),
            "JSON (*.json)",
        )
        if not file_path:
            return

        imported = import_config(file_path)
        self.settings.update(imported)
        self.language_code = self.settings.get("default_language", self.language_code)
        self._apply_language()
        self.logger.log_info(self._tr("config_imported"))

    def _on_language_changed(self) -> None:
        """Handle language switch from combo box."""
        new_lang = self.combo_language.currentData()
        self.language_code = change_language(self.language_code, new_lang)
        self._apply_language()

    def _on_theme_changed(self) -> None:
        """Handle theme switch from combo box."""
        self.theme_mode = self.combo_theme.currentData()
        self._apply_modern_style()
        QTimer.singleShot(0, self._sync_all_column_widths)

    def _on_tab_changed(self, _index: int) -> None:
        """Re-apply column widths when user switches tab."""
        QTimer.singleShot(0, self._sync_all_column_widths)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Re-apply percentage widths when main window is resized."""
        super().resizeEvent(event)
        self._sync_all_column_widths()

    def _on_error(self, message: str) -> None:
        """Handle worker errors centrally."""
        self.is_loading_drivers = False
        self.is_loading_apps = False
        self.button_load_drivers.setEnabled(True)
        self.button_load_apps.setEnabled(True)
        self.logger.log_error(message)
        QMessageBox.critical(self, self._tr("error"), message)
