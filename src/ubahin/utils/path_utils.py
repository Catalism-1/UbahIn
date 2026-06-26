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


def app_data_dir() -> Path:
    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Ubahin",
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Ubahin",
            Path(tempfile.gettempdir()) / "Ubahin",
        ]
    else:
        candidates = [
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Ubahin",
            Path(tempfile.gettempdir()) / "Ubahin",
        ]
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_test.tmp"
            probe.write_bytes(b"ok")
            probe.unlink(missing_ok=True)
            return path
        except OSError:
            continue
    raise PermissionError("Tidak ada folder data aplikasi yang dapat ditulis.")


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
