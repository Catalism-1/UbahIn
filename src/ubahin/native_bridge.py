from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Iterable

from ubahin.utils.path_utils import sanitize_filename, unique_file

try:
    import ubahin_native as _native
except Exception:  # Native module optional; Python fallback is the supported baseline.
    _native = None


def native_status() -> dict[str, object]:
    return {
        "available": _native is not None,
        "backend": "rust" if _native is not None else "python",
    }


def fast_file_hash(path: str | Path) -> str:
    file_path = Path(path)
    if _native is not None:
        return str(_native.fast_file_hash(str(file_path)))
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_files(paths: Iterable[str | Path]) -> list[dict[str, object]]:
    path_strings = [str(Path(path)) for path in paths]
    if _native is not None:
        return list(_native.scan_files(path_strings))
    rows: list[dict[str, object]] = []
    for raw_path in path_strings:
        path = Path(raw_path)
        exists = path.exists()
        stat = path.stat() if exists else None
        rows.append(
            {
                "path": str(path),
                "filename": path.name,
                "size_bytes": stat.st_size if stat else 0,
                "extension": path.suffix.lower(),
                "modified_time": stat.st_mtime if stat else None,
                "exists": exists,
            }
        )
    return rows


def safe_output_path(directory: str | Path, filename: str) -> str:
    if _native is not None:
        return str(_native.safe_output_path(str(directory), filename))
    directory_path = Path(directory)
    raw_name = filename.replace("\\", "_").replace("/", "_")
    dot_index = raw_name.rfind(".")
    if dot_index > 0:
        stem = raw_name[:dot_index]
        suffix = raw_name[dot_index:]
    else:
        stem = raw_name
        suffix = ""
    safe_name = f"{sanitize_filename(stem)}{suffix}"
    return str(unique_file(directory_path, safe_name))


def system_snapshot(output_dir: str | Path | None = None) -> dict[str, object]:
    target = Path(output_dir or Path.cwd())
    if _native is not None:
        try:
            return dict(_native.system_snapshot(str(target)))
        except TypeError:
            return dict(_native.system_snapshot())
    memory = shutil.disk_usage(target if target.exists() else Path.cwd())
    return {
        "logical_cpu_count": os.cpu_count() or 1,
        "available_memory": 0,
        "total_memory": 0,
        "available_disk": memory.free,
    }


def estimate_file_size(pages: int, dpi: int, quality: int) -> int:
    if _native is not None:
        return int(_native.estimate_file_size(pages, dpi, quality))
    dpi_factor = (dpi / 150) ** 2
    quality_factor = 0.7 + ((quality - 70) / 25) * 0.6
    return int(max(1, pages) * 300_000 * dpi_factor * quality_factor)
