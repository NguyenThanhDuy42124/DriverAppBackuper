"""MD5 helper utilities."""

from __future__ import annotations

import hashlib


def calculate_md5(file_path: str, chunk_size: int = 65536) -> str:
    """Calculate MD5 hash for a file using chunked reads."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()
