"""Desktop entry point for Ubahin.

The converter CLI remains available through ``ubahin.cli``. This file is the
launcher used by PyInstaller so the Windows executable can open without command
line arguments.
"""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def _ensure_source_layout_on_path() -> None:
    root = Path(__file__).resolve().parent
    src = root / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _fallback_log_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    log_dir = Path(base) / "Ubahin" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _write_fallback_startup_error() -> Path:
    log_path = _fallback_log_dir() / "startup.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Startup failure before app bootstrap\n")
        handle.write(traceback.format_exc())
        handle.write("\n")
    return log_path


def _show_fallback_error(log_path: Path) -> None:
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title("Ubahin - Diagnostik")
        root.geometry("520x260")
        root.minsize(480, 240)
        root.resizable(False, False)

        frame = ttk.Frame(root, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="GUI Ubahin tidak dapat dimuat", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Ubahin gagal membuka tampilan utama. Detail teknis telah disimpan di startup.log.",
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(12, 8))
        ttk.Label(frame, text=str(log_path), wraplength=460, foreground="#555555").pack(anchor="w", pady=(0, 18))

        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e", fill="x")
        ttk.Button(buttons, text="Buka folder log", command=lambda: os.startfile(log_path.parent)).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Tutup", command=root.destroy).pack(side="right")
        root.mainloop()
    except Exception:
        pass


def main() -> int:
    _ensure_source_layout_on_path()
    try:
        from ubahin.desktop.app import main as desktop_main

        return desktop_main()
    except SystemExit:
        raise
    except Exception:
        log_path = _write_fallback_startup_error()
        if "--silent" not in sys.argv:
            _show_fallback_error(log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
