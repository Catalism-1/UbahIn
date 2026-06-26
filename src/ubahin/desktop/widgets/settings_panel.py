from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable

from ubahin.desktop.theme import BORDER, FONT, FONT_SECTION, FONT_SMALL, MUTED, PANEL, PANEL_2, PRIMARY, TEXT
from ubahin.models import QualityPreset

PRESETS: dict[str, tuple[QualityPreset, int, int]] = {
    "Standard": (QualityPreset.STANDARD, 150, 80),
    "Tinggi": (QualityPreset.HIGH, 200, 90),
    "Sangat Tinggi": (QualityPreset.ULTRA, 300, 95),
}


class SettingsPanel(tk.Frame):
    def __init__(self, master: tk.Misc, change_callback: Callable[[], None]) -> None:
        super().__init__(master, bg=PANEL, padx=16, pady=16, highlightbackground=BORDER, highlightthickness=1)
        self.change_callback = change_callback
        self.output_var = tk.StringVar()
        self.preset_var = tk.StringVar(value="Tinggi")
        self.optimize_var = tk.BooleanVar(value=True)
        self.zip_var = tk.BooleanVar(value=False)
        self.open_after_var = tk.BooleanVar(value=False)
        self.summary_vars = {
            "files": tk.StringVar(value="0"),
            "pages": tk.StringVar(value="0"),
            "jpg": tk.StringVar(value="0"),
        }
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Pengaturan Hasil", bg=PANEL, fg=TEXT, font=FONT_SECTION).pack(anchor="w")

        tk.Label(self, text="Folder output", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w", pady=(18, 5))
        output_row = tk.Frame(self, bg=PANEL)
        output_row.pack(fill="x")
        self.output_entry = tk.Entry(output_row, textvariable=self.output_var, state="readonly", readonlybackground=PANEL_2, fg=TEXT, bd=0)
        self.output_entry.pack(side="left", fill="x", expand=True, ipady=7)
        tk.Button(
            output_row,
            text="Pilih Folder",
            command=self.choose_output,
            bg="#334155",
            fg=TEXT,
            activebackground="#475569",
            activeforeground=TEXT,
            bd=0,
            padx=10,
            pady=8,
            cursor="hand2",
            font=FONT_SMALL,
        ).pack(side="left", padx=(8, 0))

        tk.Label(self, text="Preset kualitas", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w", pady=(18, 6))
        for label, (_preset, dpi, quality) in PRESETS.items():
            tk.Radiobutton(
                self,
                text=f"{label} ({dpi} DPI, JPG {quality})",
                variable=self.preset_var,
                value=label,
                command=self.change_callback,
                bg=PANEL,
                fg=TEXT,
                selectcolor=PANEL_2,
                activebackground=PANEL,
                activeforeground=TEXT,
                font=FONT_SMALL,
            ).pack(anchor="w", pady=2)

        self._checkbox("Optimalkan ukuran file", self.optimize_var)
        self._checkbox("Buat ZIP hasil", self.zip_var)
        self._checkbox("Buka folder setelah selesai", self.open_after_var)

        summary = tk.Frame(self, bg=PANEL_2, padx=12, pady=12)
        summary.pack(fill="x", pady=(20, 0))
        tk.Label(summary, text="Ringkasan", bg=PANEL_2, fg=TEXT, font=FONT).pack(anchor="w", pady=(0, 8))
        self._summary_row(summary, "Jumlah PDF", self.summary_vars["files"])
        self._summary_row(summary, "Total halaman", self.summary_vars["pages"])
        self._summary_row(summary, "Estimasi JPG", self.summary_vars["jpg"])

        self.start_button = tk.Button(
            self,
            text="Mulai Ubah File",
            state="disabled",
            bg=PRIMARY,
            fg=TEXT,
            disabledforeground="#94a3b8",
            activebackground="#1d4ed8",
            activeforeground=TEXT,
            bd=0,
            padx=12,
            pady=14,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        )
        self.start_button.pack(fill="x", pady=(18, 0))

    def _checkbox(self, text: str, variable: tk.BooleanVar) -> None:
        tk.Checkbutton(
            self,
            text=text,
            variable=variable,
            command=self.change_callback,
            bg=PANEL,
            fg=TEXT,
            selectcolor=PANEL_2,
            activebackground=PANEL,
            activeforeground=TEXT,
            font=FONT_SMALL,
        ).pack(anchor="w", pady=(10, 0))

    @staticmethod
    def _summary_row(parent: tk.Frame, label: str, variable: tk.StringVar) -> None:
        row = tk.Frame(parent, bg=PANEL_2)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=PANEL_2, fg=MUTED, font=FONT_SMALL).pack(side="left")
        tk.Label(row, textvariable=variable, bg=PANEL_2, fg=TEXT, font=FONT_SMALL).pack(side="right")

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Pilih Folder Output")
        if selected:
            self.output_var.set(selected)
            self.change_callback()

    def output_path(self) -> Path | None:
        value = self.output_var.get().strip()
        return Path(value) if value else None

    def preset_values(self) -> tuple[QualityPreset, int, int, str]:
        preset, dpi, quality = PRESETS[self.preset_var.get()]
        return preset, dpi, quality, self.preset_var.get()

    def update_summary(self, files: int, pages: int) -> None:
        self.summary_vars["files"].set(str(files))
        self.summary_vars["pages"].set(str(pages))
        self.summary_vars["jpg"].set(str(pages))

    def set_start_enabled(self, enabled: bool) -> None:
        self.start_button.configure(state="normal" if enabled else "disabled")
