from __future__ import annotations

import tkinter as tk

from ubahin.desktop.theme import BORDER, FONT, FONT_SECTION, FONT_SMALL, MUTED, PANEL, PANEL_2, TEXT
from ubahin.utils import get_resource_path


class AboutPage(tk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg="#0f172a")
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        tk.Label(self, text="Tentang Ubahin", bg="#0f172a", fg=TEXT, font=FONT_SECTION).grid(row=0, column=0, sticky="w")
        tk.Label(
            self,
            text="Ubah file jadi lebih mudah.",
            bg="#0f172a",
            fg=MUTED,
            font=FONT,
        ).grid(row=1, column=0, sticky="w", pady=(6, 18))

        card = tk.Frame(self, bg=PANEL, padx=22, pady=22, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=2, column=0, sticky="ew")
        tk.Label(card, text="UBAHIN", bg=PANEL, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(card, text=f"Versi {self._version()}", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w", pady=(4, 16))

        info = tk.Frame(card, bg=PANEL_2, padx=14, pady=14)
        info.pack(fill="x")
        tk.Label(
            info,
            text="Versi demo untuk pengujian engine converter.",
            bg=PANEL_2,
            fg=TEXT,
            font=FONT,
            anchor="w",
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            info,
            text="UI ini sementara dan akan diganti dengan desain final Claude setelah siap. "
            "Engine konversi tetap lokal/offline di laptop.",
            bg=PANEL_2,
            fg=MUTED,
            font=FONT_SMALL,
            anchor="w",
            justify="left",
            wraplength=720,
        ).pack(anchor="w", pady=(8, 0))

    @staticmethod
    def _version() -> str:
        version_file = get_resource_path("VERSION")
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except OSError:
            return "0.1.1"
