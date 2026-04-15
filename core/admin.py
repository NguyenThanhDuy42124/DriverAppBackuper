"""Windows administrator privilege helpers."""

from __future__ import annotations

import ctypes
import os
import sys
from typing import Sequence


def check_admin() -> bool:
    """Return True when current process has administrator rights."""
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def request_admin(argv: Sequence[str] | None = None) -> bool:
    """Request administrator privilege by relaunching the current process."""
    if os.name != "nt" or check_admin():
        return False

    args = list(argv if argv is not None else sys.argv)
    params = " ".join(f'"{item}"' for item in args)

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        params,
        None,
        1,
    )
    return result > 32
