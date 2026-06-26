from __future__ import annotations

import importlib
import platform
import shutil
import sys
from datetime import datetime

from ubahin.desktop.self_check import run_self_check
from ubahin.native_bridge import native_status
from ubahin.utils import get_app_data_dir, get_log_dir


def _dependency_status(module_name: str) -> str:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "")
        return f"OK {version}".strip()
    except Exception as exc:
        return f"GAGAL {type(exc).__name__}: {exc}"


def build_report() -> str:
    app_dir = get_app_data_dir()
    log_dir = get_log_dir()
    disk = shutil.disk_usage(app_dir)
    self_check = run_self_check()
    native = native_status()
    lines = [
        "Ubahin Diagnostic Report",
        f"Dibuat: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Windows/platform: {platform.platform()}",
        f"Python: {sys.version}",
        f"Arsitektur Python: {platform.architecture()[0]}",
        f"Arsitektur mesin: {platform.machine()}",
        f"App data: {app_dir}",
        f"Log dir: {log_dir}",
        f"Free disk app data: {disk.free} bytes",
        "",
        "Dependency:",
        f"- PyMuPDF/fitz: {_dependency_status('fitz')}",
        f"- Pillow/PIL: {_dependency_status('PIL')}",
        f"- pypdf: {_dependency_status('pypdf')}",
        "",
        f"Native module: {'aktif' if native.get('available') else 'fallback Python'} ({native.get('backend')})",
        f"Self-check: {'OK' if self_check.ok else 'GAGAL'}",
    ]
    for item in self_check.checks:
        status = "OK" if item.ok else "GAGAL"
        lines.append(f"- {status} {item.name}: {item.message}")
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report()
    output_path = get_log_dir() / "diagnostic_report.txt"
    output_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Laporan disimpan: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
