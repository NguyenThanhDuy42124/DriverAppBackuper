"""Driver loading and filtering logic."""

from __future__ import annotations

import csv
import io
import subprocess
from typing import Dict, List


DriverInfo = Dict[str, str]


def _pick_value(row: Dict[str, str], candidates: List[str]) -> str:
    """Pick the first non-empty value from candidate keys."""
    for key in candidates:
        value = row.get(key, "").strip()
        if value:
            return value
    return ""


def _run_driver_query() -> str:
    """Execute DRIVERQUERY and return CSV output text."""
    command = ["DRIVERQUERY", "/FO", "CSV", "/SI"]
    raw_result = subprocess.run(command, capture_output=True)
    if raw_result.returncode != 0:
        error_text = raw_result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error_text or "Unable to run DRIVERQUERY")

    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw_result.stdout.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_result.stdout.decode("utf-8", errors="replace")


def parse_driver_csv(csv_text: str) -> List[DriverInfo]:
    """Parse DRIVERQUERY CSV output into normalized driver records."""
    reader = csv.DictReader(io.StringIO(csv_text))
    drivers: List[DriverInfo] = []
    for row in reader:
        device_name = _pick_value(row, ["DeviceName", "Display Name", "Device Name", "Module Name"])
        inf_name = _pick_value(row, ["InfName", "Inf Name", "INF Name"])
        if not inf_name:
            continue
        status = _pick_value(row, ["State", "Status", "IsSigned", "Driver Type"]) or "Unknown"

        drivers.append(
            {
                "device_name": device_name,
                "inf_name": inf_name,
                "status": status,
            }
        )
    return drivers


def get_driver_list() -> List[DriverInfo]:
    """Fetch all signed drivers and return parsed records."""
    csv_text = _run_driver_query()
    return parse_driver_csv(csv_text)


def filter_drivers(drivers: List[DriverInfo], filter_status: str) -> List[DriverInfo]:
    """Filter drivers by status value or return all when filter is 'all'."""
    if filter_status.lower() == "all":
        return drivers
    status_key = filter_status.lower()
    return [item for item in drivers if status_key in item["status"].lower()]


def search_driver(drivers: List[DriverInfo], keyword: str) -> List[DriverInfo]:
    """Search drivers by device name, inf name, or status."""
    query = keyword.strip().lower()
    if not query:
        return drivers

    def _matched(driver: DriverInfo) -> bool:
        values = (driver["device_name"], driver["inf_name"], driver["status"])
        return any(query in value.lower() for value in values)

    return [driver for driver in drivers if _matched(driver)]
