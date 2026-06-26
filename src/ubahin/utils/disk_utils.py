from __future__ import annotations

import os
import shutil
from pathlib import Path


def ensure_writable_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if not os.access(path, os.W_OK):
        raise PermissionError("Folder hasil tidak dapat ditulis.")
    probe = path / ".ubahin_write_test.tmp"
    try:
        probe.write_bytes(b"ok")
    finally:
        probe.unlink(missing_ok=True)


def available_disk_bytes(path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(path).free


def has_enough_space(path: Path, required_bytes: int, safety_factor: float = 1.1) -> bool:
    try:
        return available_disk_bytes(path) >= int(required_bytes * safety_factor)
    except OSError:
        return True
