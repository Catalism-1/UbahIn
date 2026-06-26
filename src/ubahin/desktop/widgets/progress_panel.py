from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ubahin.desktop.theme import BORDER, FONT, FONT_SMALL, MUTED, PANEL, TEXT


class ProgressPanel(tk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=PANEL, padx=14, pady=12, highlightbackground=BORDER, highlightthickness=1)
        self.active_file_var = tk.StringVar(value="File aktif: -")
        self.page_var = tk.StringVar(value="Halaman 0 dari 0")
        self.file_var = tk.StringVar(value="0 dari 0 file selesai")
        self.status_var = tk.StringVar(value="Belum ada proses berjalan.")
        self.overall_var = tk.DoubleVar(value=0)
        self.file_progress_var = tk.DoubleVar(value=0)
        self._build()

    def _build(self) -> None:
        tk.Label(self, textvariable=self.active_file_var, bg=PANEL, fg=TEXT, font=FONT).pack(anchor="w")
        tk.Label(self, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w", pady=(2, 8))

        tk.Label(self, text="Progress keseluruhan", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w")
        ttk.Progressbar(self, variable=self.overall_var, maximum=100, style="Ubahin.Horizontal.TProgressbar").pack(fill="x", pady=(3, 8))
        tk.Label(self, text="Progress file aktif", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w")
        ttk.Progressbar(self, variable=self.file_progress_var, maximum=100, style="Ubahin.Horizontal.TProgressbar").pack(
            fill="x", pady=(3, 8)
        )

        info = tk.Frame(self, bg=PANEL)
        info.pack(fill="x")
        tk.Label(info, textvariable=self.page_var, bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left")
        tk.Label(info, textvariable=self.file_var, bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="right")

    def reset(self) -> None:
        self.active_file_var.set("File aktif: -")
        self.page_var.set("Halaman 0 dari 0")
        self.file_var.set("0 dari 0 file selesai")
        self.status_var.set("Belum ada proses berjalan.")
        self.overall_var.set(0)
        self.file_progress_var.set(0)

    def set_progress(
        self,
        *,
        filename: str,
        file_done: int,
        file_total: int,
        completed_pages: int,
        total_pages: int,
        completed_files: int,
        total_files: int,
        status: str,
    ) -> None:
        self.active_file_var.set(f"File aktif: {filename or '-'}")
        self.page_var.set(f"Halaman {file_done} dari {file_total}")
        self.file_var.set(f"{completed_files} dari {total_files} file selesai")
        self.status_var.set(status)
        overall = (completed_pages / total_pages * 100) if total_pages else 0
        current_file = (file_done / file_total * 100) if file_total else 0
        self.overall_var.set(min(max(overall, 0), 100))
        self.file_progress_var.set(min(max(current_file, 0), 100))
