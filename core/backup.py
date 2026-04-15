"""Driver backup logic with reusable functions for GUI and CLI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from typing import Callable, Dict, List, Tuple

from core.md5_utils import calculate_md5


DriverInfo = Dict[str, str]
ProgressCallback = Callable[[int, str], None]
_INDEX_SCAN_THRESHOLD = 300


def prepare_backup_folder(base_folder: str, prefix: str = "drivers_backup") -> Path:
    """Create and return a timestamped backup folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(base_folder) / f"{prefix}_{timestamp}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _normalize_device_name(device_name: str) -> str:
    """Normalize a device name into a folder-safe name."""
    safe = "".join(char if char.isalnum() or char in " _-" else "_" for char in device_name)
    return safe.strip() or "unknown_device"


def _get_whql_inf_path(inf_name: str) -> Path:
    """Resolve INF path under Windows INF root."""
    return Path(r"C:\Windows\INF") / inf_name


def _build_driver_store_index(driver_store_root: str) -> Dict[str, Path]:
    """Index DriverStore INF files by MD5 for fast repeated lookup."""
    index: Dict[str, Path] = {}
    store_root = Path(driver_store_root)

    for inf_file in store_root.rglob("*.inf"):
        try:
            md5 = calculate_md5(str(inf_file))
        except OSError:
            continue
        index.setdefault(md5, inf_file.parent)
    return index


def find_driver_in_store(
    inf_name: str,
    driver_store_root: str,
    driver_store_index: Dict[str, Path] | None = None,
    whql_md5_cache: Dict[str, str] | None = None,
) -> Path | None:
    """Find a matching INF in DriverStore by MD5 against Windows INF file."""
    whql_inf = _get_whql_inf_path(inf_name)
    if not whql_inf.exists():
        return None

    if whql_md5_cache is not None and inf_name in whql_md5_cache:
        target_md5 = whql_md5_cache[inf_name]
    else:
        target_md5 = calculate_md5(str(whql_inf))
        if whql_md5_cache is not None:
            whql_md5_cache[inf_name] = target_md5

    if driver_store_index is not None:
        return driver_store_index.get(target_md5)

    store_root = Path(driver_store_root)

    for inf_file in store_root.rglob("*.inf"):
        try:
            if calculate_md5(str(inf_file)) == target_md5:
                return inf_file.parent
        except OSError:
            continue
    return None


def copy_driver_files(source_dir: Path, destination_dir: Path) -> None:
    """Copy a driver directory tree to destination."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)


def _deduplicate_drivers(selected_drivers: List[DriverInfo]) -> List[DriverInfo]:
    """Remove duplicate INF entries while preserving input order."""
    seen = set()
    result: List[DriverInfo] = []
    for driver in selected_drivers:
        inf_name = driver.get("inf_name", "")
        if inf_name in seen:
            continue
        seen.add(inf_name)
        result.append(driver)
    return result


def _count_unique_inf_names(drivers: List[DriverInfo]) -> int:
    """Count unique non-empty INF names in selected drivers."""
    return len({driver.get("inf_name", "") for driver in drivers if driver.get("inf_name", "")})


def backup_selected_drivers(
    selected_drivers: List[DriverInfo],
    output_folder: str,
    mode: str = "full",
    driver_store_root: str = r"C:\Windows\System32\DriverStore\FileRepository",
    progress_callback: ProgressCallback | None = None,
) -> Dict[str, int]:
    """Backup selected drivers from DriverStore into a timestamped folder."""
    if not selected_drivers:
        return {"total": 0, "success": 0, "failed": 0}

    drivers = selected_drivers if mode == "full" else _deduplicate_drivers(selected_drivers)
    target_root = prepare_backup_folder(output_folder)
    unique_inf_count = _count_unique_inf_names(drivers)
    driver_store_index = (
        _build_driver_store_index(driver_store_root) if unique_inf_count >= _INDEX_SCAN_THRESHOLD else None
    )
    whql_md5_cache: Dict[str, str] = {}
    store_lookup_cache: Dict[str, Path | None] = {}

    success_count = 0
    fail_count = 0
    total = len(drivers)

    for index, driver in enumerate(drivers, start=1):
        inf_name = driver.get("inf_name", "")
        device_name = driver.get("device_name", "unknown_device")
        if inf_name in store_lookup_cache:
            store_path = store_lookup_cache[inf_name]
        else:
            store_path = find_driver_in_store(
                inf_name,
                driver_store_root,
                driver_store_index=driver_store_index,
                whql_md5_cache=whql_md5_cache,
            )
            store_lookup_cache[inf_name] = store_path

        if store_path is None:
            fail_count += 1
            if progress_callback:
                progress_callback(int((index / total) * 100), f"Skip {inf_name}: not found")
            continue

        destination = target_root / _normalize_device_name(device_name)
        copy_driver_files(store_path, destination)
        success_count += 1

        if progress_callback:
            progress_callback(
                int((index / total) * 100),
                f"Backed up {device_name} ({inf_name})",
            )

    return {"total": total, "success": success_count, "failed": fail_count}


def quick_backup(
    selected_drivers: List[DriverInfo],
    output_folder: str,
    progress_callback: ProgressCallback | None = None,
) -> Dict[str, int]:
    """Perform strict backup quickly for selected drivers."""
    return backup_selected_drivers(
        selected_drivers=selected_drivers,
        output_folder=output_folder,
        mode="strict",
        progress_callback=progress_callback,
    )


def full_backup_system(
    selected_drivers: List[DriverInfo],
    output_folder: str,
    app_backup_callback: Callable[[Path], Dict[str, int]] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Tuple[Dict[str, int], Dict[str, int] | None]:
    """Backup drivers and optionally applications in one run."""
    driver_summary = backup_selected_drivers(
        selected_drivers=selected_drivers,
        output_folder=output_folder,
        mode="full",
        progress_callback=progress_callback,
    )

    app_summary = None
    if app_backup_callback:
        app_summary = app_backup_callback(prepare_backup_folder(output_folder, "apps_backup"))
    return driver_summary, app_summary
