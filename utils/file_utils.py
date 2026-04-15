"""File utilities for JSON config import/export and folder operations."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load a JSON object from disk."""
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("JSON content must be an object")
    return data


def save_json_file(file_path: str, data: Dict[str, Any]) -> None:
    """Save a JSON object to disk with pretty formatting."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def export_config(config_data: Dict[str, Any], export_path: str) -> None:
    """Export configuration to a target JSON path."""
    save_json_file(export_path, config_data)


def import_config(import_path: str) -> Dict[str, Any]:
    """Import configuration JSON from a path."""
    return load_json_file(import_path)


def open_folder(folder_path: str) -> None:
    """Open a folder in Windows Explorer."""
    path = Path(folder_path)
    if not path.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    if os.name == "nt":
        os.startfile(str(path))
        return

    subprocess.run(["xdg-open", str(path)], check=True)
