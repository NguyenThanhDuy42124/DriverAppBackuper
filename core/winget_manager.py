"""WinGet app backup and restore helpers."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Callable, Dict, List


AppInfo = Dict[str, str]
ProgressCallback = Callable[[int, str], None]
_COLUMN_SPLIT_RE = re.compile(r"\s{2,}")


def _safe_text(value: object) -> str:
    """Convert potential None/object values to safe string text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        for encoding in ("utf-8", "cp1252", "cp850", "latin-1"):
            try:
                return value.decode(encoding)
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace")
    return str(value)


def _run_winget_command(args: List[str]) -> tuple[int, str, str]:
    """Run a winget command and return (returncode, stdout, stderr)."""
    result = subprocess.run(["winget", *args], capture_output=True, text=False)
    stdout = _safe_text(result.stdout)
    stderr = _safe_text(result.stderr)
    return result.returncode, stdout, stderr


def _parse_winget_list_table(output: str) -> List[AppInfo]:
    """Parse the text table from 'winget list'."""
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if not lines:
        return []

    data_lines = [line for line in lines if not line.startswith("-")]
    apps: List[AppInfo] = []

    for line in data_lines[1:]:
        parts = _COLUMN_SPLIT_RE.split(line.strip())
        if len(parts) < 2:
            continue

        name = parts[0]
        app_id = parts[1]
        version = parts[2] if len(parts) > 2 else ""
        source = parts[-1] if len(parts) > 3 else ""

        if name.lower() == "name" and app_id.lower() == "id":
            continue

        apps.append(
            {
                "name": name,
                "id": app_id,
                "version": version,
                "source": source,
                "status": "Installed",
            }
        )
    return apps


def _parse_winget_export_json(file_path: Path) -> List[AppInfo]:
    """Parse winget export json into app list."""
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    sources = data.get("Sources", [])
    apps: List[AppInfo] = []

    for source in sources:
        source_name = source.get("SourceDetails", {}).get("Name", "")
        for package in source.get("Packages", []):
            app_id = package.get("PackageIdentifier", "")
            apps.append(
                {
                    "name": app_id,
                    "id": app_id,
                    "version": "",
                    "source": source_name,
                    "status": "Installed",
                }
            )
    return apps


def get_installed_apps() -> List[AppInfo]:
    """Get installed applications from winget list/export."""
    return_code, stdout, _ = _run_winget_command(["list"])
    if return_code == 0 and stdout.strip():
        apps = _parse_winget_list_table(stdout)
        if apps:
            return apps

    temp_file = Path("apps_export_temp.json")
    return_code, stdout, stderr = _run_winget_command(["export", "-o", str(temp_file)])
    if return_code != 0:
        error_text = stderr.strip() or stdout.strip()
        raise RuntimeError(error_text or "Unable to query winget applications")

    try:
        return _parse_winget_export_json(temp_file)
    finally:
        if temp_file.exists():
            temp_file.unlink()


def export_apps_to_file(path: str) -> str:
    """Export all installed apps to JSON backup file path."""
    apps = get_installed_apps()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as file:
        json.dump(apps, file, ensure_ascii=False, indent=2)
    return str(output)


def export_selected_apps_to_file(apps: List[AppInfo], path: str) -> str:
    """Export selected app list to JSON or CSV based on extension."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.suffix.lower() == ".csv":
        import csv

        with output.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["name", "id", "version", "source"])
            writer.writeheader()
            for app in apps:
                writer.writerow({k: app.get(k, "") for k in ["name", "id", "version", "source"]})
    else:
        with output.open("w", encoding="utf-8") as file:
            json.dump(apps, file, ensure_ascii=False, indent=2)
    return str(output)


def import_apps_from_file(path: str) -> List[AppInfo]:
    """Import app backup list from JSON file."""
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Invalid app backup format")

    return [
        {
            "name": item.get("name", item.get("id", "")),
            "id": item.get("id", ""),
            "version": item.get("version", ""),
            "source": item.get("source", ""),
            "status": item.get("status", "Not installed"),
        }
        for item in data
    ]


def _timestamped_backup_name() -> str:
    """Build default backup filename for app backups."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"apps_backup_{timestamp}.json"


def default_backup_path(base_folder: str) -> str:
    """Return default timestamped backup path in a base folder."""
    return str(Path(base_folder) / _timestamped_backup_name())


def install_app(app_id: str, retries: int = 1) -> tuple[bool, str]:
    """Install one app by winget id with retry support."""
    command = ["install", "--id", app_id, "-e", "--silent"]
    attempts = max(1, retries + 1)

    for _ in range(attempts):
        return_code, stdout, stderr = _run_winget_command(command)
        if return_code == 0:
            return True, stdout.strip() or "Installed"
    return False, stderr.strip() or stdout.strip() or "Installation failed"


def install_multiple_apps(
    app_list: List[AppInfo],
    progress_callback: ProgressCallback | None = None,
    retries: int = 1,
    skip_installed: bool = True,
) -> Dict[str, int]:
    """Install many apps sequentially with progress callback."""
    installed_ids = {item.get("id", "") for item in get_installed_apps()} if skip_installed else set()
    total = len(app_list)
    success_count = 0
    fail_count = 0
    skipped_count = 0

    for index, app in enumerate(app_list, start=1):
        app_id = app.get("id", "")
        app_name = app.get("name", app_id)

        if skip_installed and app_id in installed_ids:
            skipped_count += 1
            if progress_callback:
                progress_callback(int((index / total) * 100), f"Skip installed: {app_name}")
            continue

        ok, message = install_app(app_id, retries=retries)
        if ok:
            success_count += 1
            app["status"] = "Installed"
        else:
            fail_count += 1
            app["status"] = "Not installed"

        if progress_callback:
            status = "Success" if ok else "Failed"
            progress_callback(int((index / total) * 100), f"{status} {app_name}: {message}")

    return {
        "total": total,
        "success": success_count,
        "failed": fail_count,
        "skipped": skipped_count,
    }


def search_app(apps: List[AppInfo], keyword: str) -> List[AppInfo]:
    """Search apps by name/id/version/source."""
    query = keyword.strip().lower()
    if not query:
        return apps

    def _matches(app: AppInfo) -> bool:
        fields = [app.get("name", ""), app.get("id", ""), app.get("version", ""), app.get("source", "")]
        return any(query in _safe_text(field).lower() for field in fields)

    return [app for app in apps if _matches(app)]


def filter_apps_by_source(apps: List[AppInfo], source_name: str) -> List[AppInfo]:
    """Filter app list by source. 'all' returns unfiltered list."""
    if source_name.lower() == "all":
        return apps
    return [app for app in apps if source_name.lower() in _safe_text(app.get("source", "")).lower()]


def export_restore_script(apps: List[AppInfo], path: str) -> str:
    """Export a batch script that installs all selected apps."""
    script_path = Path(path)
    script_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["@echo off", "echo Restoring applications with winget..."]
    for app in apps:
        app_id = app.get("id", "")
        if app_id:
            lines.append(f"winget install --id {app_id} -e --silent")
    lines.append("echo Done")

    script_path.write_text("\n".join(lines), encoding="utf-8")
    return str(script_path)
