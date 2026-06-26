from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path

from ubahin.utils import get_log_dir


def write_startup_exception(exc: BaseException | None = None) -> Path:
    log_path = get_log_dir() / "startup.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Startup failure\n")
        if exc is not None:
            handle.write(f"{type(exc).__name__}: {exc}\n")
        handle.write(traceback.format_exc())
        handle.write("\n")
    return log_path


def show_startup_error_dialog(log_path: Path) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Ubahin tidak dapat dibuka",
            "Ubahin tidak dapat dibuka. Detail teknis telah disimpan di folder log.\n\n"
            f"Lokasi log:\n{log_path}",
        )
        root.destroy()
    except Exception:
        pass
