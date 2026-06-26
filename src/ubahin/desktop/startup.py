from __future__ import annotations

import os
import traceback
from datetime import datetime
from pathlib import Path

from ubahin.utils import get_log_dir, open_in_file_manager


def write_startup_exception(exc: BaseException | None = None) -> Path:
    log_path = get_log_dir() / "startup.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Startup failure\n")
        if exc is not None:
            handle.write(f"{type(exc).__name__}: {exc}\n")
        handle.write(traceback.format_exc())
        handle.write("\n")
    return log_path


def _open_log_folder(log_path: Path) -> None:
    try:
        open_in_file_manager(log_path.parent)
    except Exception:
        if os.name == "nt":
            os.startfile(log_path.parent)  # type: ignore[attr-defined]


def show_startup_error_dialog(log_path: Path) -> None:
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

        title = ttk.Label(frame, text="GUI Ubahin tidak dapat dimuat", font=("Segoe UI", 13, "bold"))
        title.pack(anchor="w")

        message = (
            "Ubahin gagal membuka tampilan utama. Backend sudah menulis detail error "
            "ke startup.log. Buka folder log untuk melihat penyebab teknisnya."
        )
        body = ttk.Label(frame, text=message, wraplength=460, justify="left")
        body.pack(anchor="w", pady=(12, 8))

        path_label = ttk.Label(frame, text=str(log_path), wraplength=460, foreground="#555555")
        path_label.pack(anchor="w", pady=(0, 18))

        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e", fill="x")
        ttk.Button(buttons, text="Buka folder log", command=lambda: _open_log_folder(log_path)).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Tutup", command=root.destroy).pack(side="right")

        root.mainloop()
    except Exception:
        try:
            import tkinter.messagebox as messagebox

            messagebox.showerror(
                "Ubahin tidak dapat dibuka",
                "GUI Ubahin tidak dapat dimuat. Detail teknis telah disimpan di:\n\n" f"{log_path}",
            )
        except Exception:
            pass
