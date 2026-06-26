from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ubahin.desktop.pages.about_page import AboutPage
from ubahin.desktop.pages.pdf_to_jpg_page import PdfToJpgPage
from ubahin.desktop.pages.system_check_page import SystemCheckPage
from ubahin.desktop.theme import BG, FONT, FONT_SMALL, FONT_TITLE, MUTED, PANEL, PRIMARY, TEXT, configure_ttk


class MainWindow:
    def __init__(self) -> None:
        configure_ttk()
        self.root = tk.Tk()
        self.root.title("Ubahin")
        self.root.geometry("1120x720")
        self.root.minsize(980, 640)
        self.root.configure(bg=BG)

        self.status_var = tk.StringVar(value="Siap")
        self._pages: dict[str, tk.Frame] = {}
        self._nav_buttons: dict[str, tk.Button] = {}

        self._build_layout()
        self.show_page("pdf")

    def run(self) -> None:
        self.root.mainloop()

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _build_layout(self) -> None:
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        header = tk.Frame(self.root, bg=BG, padx=24, pady=18)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        title = tk.Label(header, text="UBAHIN", bg=BG, fg=TEXT, font=FONT_TITLE)
        title.pack(side="left")
        subtitle = tk.Label(header, text="Ubah file jadi lebih mudah.", bg=BG, fg=MUTED, font=("Segoe UI", 11))
        subtitle.pack(side="left", padx=(16, 0), pady=(8, 0))

        sidebar = tk.Frame(self.root, bg=PANEL, padx=14, pady=16, width=190)
        sidebar.grid(row=1, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        nav_items = [
            ("pdf", "PDF ke JPG"),
            ("system", "Pemeriksaan Sistem"),
            ("about", "Tentang Ubahin"),
        ]
        for key, label in nav_items:
            button = tk.Button(
                sidebar,
                text=label,
                command=lambda name=key: self.show_page(name),
                anchor="w",
                bd=0,
                padx=12,
                pady=11,
                bg=PANEL,
                fg=TEXT,
                activebackground=PRIMARY,
                activeforeground=TEXT,
                font=FONT,
                cursor="hand2",
            )
            button.pack(fill="x", pady=3)
            self._nav_buttons[key] = button

        self.content = tk.Frame(self.root, bg=BG, padx=18, pady=0)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._pages["pdf"] = PdfToJpgPage(self.content, status_callback=self.set_status)
        self._pages["system"] = SystemCheckPage(self.content, status_callback=self.set_status)
        self._pages["about"] = AboutPage(self.content)
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        footer = tk.Frame(self.root, bg=PANEL, padx=16, pady=8)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        tk.Label(footer, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left")
        ttk.Separator(footer, orient="vertical").pack(side="left", fill="y", padx=12)
        tk.Label(footer, text="Demo UI sementara - engine lokal/offline", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left")

    def show_page(self, name: str) -> None:
        page = self._pages[name]
        page.tkraise()
        for key, button in self._nav_buttons.items():
            if key == name:
                button.configure(bg=PRIMARY)
            else:
                button.configure(bg=PANEL)
        if name == "pdf":
            self.set_status("PDF ke JPG siap digunakan.")
        elif name == "system":
            self.set_status("Pemeriksaan sistem siap.")
        else:
            self.set_status("Tentang Ubahin.")
