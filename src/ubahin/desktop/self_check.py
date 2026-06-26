from __future__ import annotations

import argparse
import importlib
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ubahin.native_bridge import native_status
from ubahin.services import HistoryService
from ubahin.utils import get_app_data_dir, get_log_dir


@dataclass(slots=True)
class CheckItem:
    name: str
    ok: bool
    message: str


@dataclass(slots=True)
class SelfCheckReport:
    ok: bool
    generated_at: str
    app_data_dir: str
    log_dir: str
    native: dict[str, object]
    checks: list[CheckItem]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checks"] = [asdict(item) for item in self.checks]
        return data


def _check_import(module_name: str, label: str) -> CheckItem:
    try:
        importlib.import_module(module_name)
        return CheckItem(label, True, "OK")
    except Exception as exc:
        return CheckItem(label, False, f"{type(exc).__name__}: {exc}")


def _check_directory(path: Path, label: str) -> CheckItem:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return CheckItem(label, True, str(path))
    except Exception as exc:
        return CheckItem(label, False, f"{type(exc).__name__}: {exc}")


def _check_sqlite_history() -> CheckItem:
    try:
        service = HistoryService()
        service.list_recent(limit=1)
        with sqlite3.connect(service.database_path) as connection:
            connection.execute("SELECT 1").fetchone()
        return CheckItem("SQLite history", True, str(service.database_path))
    except Exception as exc:
        return CheckItem("SQLite history", False, f"{type(exc).__name__}: {exc}")


def _write_report(report: SelfCheckReport) -> Path:
    log_path = get_log_dir() / "self_check.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        handle.write("\n")
    return log_path


def run_self_check() -> SelfCheckReport:
    app_dir = get_app_data_dir()
    log_dir = get_log_dir()
    checks = [
        _check_directory(app_dir, "Folder app data"),
        _check_directory(log_dir, "Folder log"),
        _check_directory(app_dir / "settings", "Folder settings"),
        _check_directory(app_dir / "history", "Folder history"),
        _check_directory(app_dir / "cache", "Folder cache"),
        _check_sqlite_history(),
        _check_import("fitz", "PyMuPDF"),
        _check_import("PIL", "Pillow"),
        _check_import("pypdf", "pypdf"),
    ]
    native = native_status()
    native_message = "Aktif" if native.get("available") else "Tidak aktif - fallback Python"
    checks.append(CheckItem("Native acceleration", True, native_message))
    report = SelfCheckReport(
        ok=all(item.ok for item in checks),
        generated_at=datetime.now().isoformat(timespec="seconds"),
        app_data_dir=str(app_dir),
        log_dir=str(log_dir),
        native=native,
        checks=checks,
    )
    _write_report(report)
    return report


def format_report(report: SelfCheckReport) -> str:
    lines = [
        f"Ubahin self-check: {'OK' if report.ok else 'GAGAL'}",
        f"App data: {report.app_data_dir}",
        f"Log: {report.log_dir}",
        f"Native: {report.native.get('backend')} ({'aktif' if report.native.get('available') else 'fallback Python'})",
        "",
    ]
    for item in report.checks:
        status = "OK" if item.ok else "GAGAL"
        lines.append(f"[{status}] {item.name}: {item.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ubahin internal self-check")
    parser.add_argument("--silent", action="store_true", help="Tidak menampilkan dialog interaktif.")
    parser.add_argument("--json", action="store_true", help="Cetak laporan JSON.")
    args = parser.parse_args(argv)
    report = run_self_check()
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
