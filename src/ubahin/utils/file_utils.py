from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def coerce_paths(paths: Iterable[str | Path]) -> list[Path]:
    return [Path(path).expanduser().resolve() for path in paths]


def coerce_pdf_paths(paths: Iterable[str | Path]) -> list[Path]:
    return coerce_paths(paths)


def file_size(path: Path) -> int:
    return Path(path).stat().st_size


def human_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size_bytes} B"


def open_in_file_manager(path: Path) -> None:
    path = Path(path)
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
