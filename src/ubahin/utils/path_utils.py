from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def _ensure_writable_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".write_test.tmp"
    probe.write_bytes(b"ok")
    probe.unlink(missing_ok=True)
    return path


def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Ubahin",
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Ubahin",
            Path(tempfile.gettempdir()) / "Ubahin",
        ]
    else:
        candidates = [
            Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Ubahin",
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Ubahin",
            Path(tempfile.gettempdir()) / "Ubahin",
        ]
    for path in candidates:
        try:
            return _ensure_writable_directory(path)
        except OSError:
            continue
    raise PermissionError("Tidak ada folder data aplikasi yang dapat ditulis.")


def app_data_dir() -> Path:
    return get_app_data_dir()


def get_log_dir() -> Path:
    return _ensure_writable_directory(get_app_data_dir() / "logs")


def get_resource_path(relative_path: str | Path = "") -> Path:
    relative = Path(relative_path)
    if is_frozen_app() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / relative
    return Path(__file__).resolve().parents[3] / relative


def sanitize_filename(name: str, fallback: str = "file") -> str:
    safe = INVALID_WINDOWS_CHARS.sub("_", name)
    safe = re.sub(r"\s+", " ", safe).strip().strip(".")
    if not safe:
        safe = fallback
    if safe.upper() in RESERVED_WINDOWS_NAMES:
        safe = f"{safe}_file"
    return safe[:120].rstrip(" .") or fallback


def unique_directory(parent: Path, desired_name: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    base = sanitize_filename(desired_name)
    candidate = parent / base
    index = 1
    while candidate.exists():
        candidate = parent / f"{base}_{index:02d}"
        index += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def unique_file(parent: Path, filename: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    original = Path(filename)
    stem = sanitize_filename(original.stem)
    suffix = original.suffix
    candidate = parent / f"{stem}{suffix}"
    index = 1
    while candidate.exists():
        candidate = parent / f"{stem}_{index:02d}{suffix}"
        index += 1
    return candidate


def atomic_temp_path(final_path: Path) -> Path:
    return final_path.with_name(f".{final_path.stem}.tmp{final_path.suffix}")


def finalize_atomic_write(temp_path: Path, final_path: Path) -> None:
    os.replace(temp_path, final_path)


def remove_temp_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
