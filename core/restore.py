"""Driver restore logic using pnputil."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Callable, Dict, List


ProgressCallback = Callable[[int, str], None]


def install_driver_inf(inf_path: str) -> tuple[bool, str]:
    """Install a driver INF file using pnputil."""
    command = ["pnputil", "/add-driver", inf_path, "/install"]
    result = subprocess.run(command, capture_output=True, text=True)
    output = result.stdout.strip() or result.stderr.strip()
    return result.returncode == 0, output


def _find_inf_files(folder_path: str) -> List[Path]:
    """Find all INF files under a folder recursively."""
    root = Path(folder_path)
    return list(root.rglob("*.inf"))


def restore_from_folder(
    folder_path: str,
    progress_callback: ProgressCallback | None = None,
) -> Dict[str, int]:
    """Restore all INF drivers from a backup folder."""
    inf_files = _find_inf_files(folder_path)
    if not inf_files:
        raise FileNotFoundError("No INF files found in restore folder")

    success_count = 0
    fail_count = 0
    total = len(inf_files)

    for index, inf_file in enumerate(inf_files, start=1):
        ok, message = install_driver_inf(str(inf_file))
        percent = int((index / total) * 100)
        if ok:
            success_count += 1
        else:
            fail_count += 1
        if progress_callback:
            progress_callback(percent, f"{inf_file.name}: {message}")

    return {"total": total, "success": success_count, "failed": fail_count}
