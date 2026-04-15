"""Logging utilities for file logging and GUI sink support."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

GuiSink = Callable[[str], None]


class AppLogger:
    """Application logger wrapper for file and GUI logging."""

    def __init__(self, log_file: str, debug_mode: bool = False) -> None:
        self._gui_sink: Optional[GuiSink] = None
        self._logger = logging.getLogger("driverbackup")
        self._logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        self._logger.handlers.clear()

        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

    def set_gui_sink(self, sink: GuiSink) -> None:
        """Attach a GUI sink callback to mirror logs in the UI."""
        self._gui_sink = sink

    def write_log_file(self, level: int, message: str) -> None:
        """Write a message into the configured log file."""
        self._logger.log(level, message)

    def log_info(self, message: str) -> None:
        """Write an info log and mirror it to GUI sink."""
        self.write_log_file(logging.INFO, message)
        if self._gui_sink:
            self._gui_sink(message)

    def log_error(self, message: str) -> None:
        """Write an error log and mirror it to GUI sink."""
        self.write_log_file(logging.ERROR, message)
        if self._gui_sink:
            self._gui_sink(message)
