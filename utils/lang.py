"""Language utilities for multi-language UI text."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_language(file_path: str) -> Dict[str, Dict[str, str]]:
    """Load language dictionary from a JSON file."""
    lang_path = Path(file_path)
    if not lang_path.exists():
        raise FileNotFoundError(f"Language file not found: {file_path}")

    with lang_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Language file must contain a JSON object")
    return data


def change_language(current_language: str, new_language: str) -> str:
    """Validate and return the language code to use."""
    if new_language in {"vi", "en"}:
        return new_language
    return current_language


def translate(
    language_data: Dict[str, Dict[str, str]],
    key: str,
    language_code: str,
    **kwargs: Any,
) -> str:
    """Translate a key by language code and interpolate placeholders."""
    key_data = language_data.get(key, {})
    if not key_data:
        return key

    text = key_data.get(language_code) or key_data.get("en") or key
    if kwargs:
        return text.format(**kwargs)
    return text
