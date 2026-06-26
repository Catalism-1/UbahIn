from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ubahin.desktop.theme import BORDER, FONT, FONT_SMALL, MUTED, PANEL, PANEL_2, SUBTLE, TEXT
from ubahin.utils import human_size


@dataclass(slots=True)
class PdfQueueItem:
    path: Path
    size_bytes: int
    pages: int | None = None
    status: str = "Siap"
    error: str = ""

    @property
    def key(self) -> str:
        return str(self.path)


class FileQueue(tk.Frame):
    def __init__(self, master: tk.Misc, remove_callback: Callable[[str], None]) -> None:
        super().__init__(master, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        self.remove_callback = remove_callback
        self.items: dict[str, PdfQueueItem] = {}
        self._row_widgets: dict[str, tk.Frame] = {}
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=PANEL_2, padx=12, pady=9)
        header.grid(row=0, column=0, sticky="ew")
        for index, text in enumerate(["Nama file", "Ukuran", "Halaman", "Status", ""]):
            weight = 3 if index == 0 else 1
            header.grid_columnconfigure(index, weight=weight, minsize=80)
            tk.Label(header, text=text, bg=PANEL_2, fg=MUTED, font=FONT_SMALL, anchor="w").grid(row=0, column=index, sticky="ew")

        self.canvas = tk.Canvas(self, bg=PANEL, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.rows = tk.Frame(self.canvas, bg=PANEL)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.rows.bind("<Configure>", self._on_rows_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.empty_label = tk.Label(
            self.rows,
            text="Belum ada file PDF. Pilih file untuk mulai mengubah.",
            bg=PANEL,
            fg=SUBTLE,
            font=FONT,
            pady=32,
        )
        self.empty_label.pack(fill="x")

    def _on_rows_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def set_items(self, items: list[PdfQueueItem]) -> None:
        self.items = {item.key: item for item in items}
        self.refresh()

    def update_item(self, key: str, *, pages: int | None = None, status: str | None = None, error: str | None = None) -> None:
        item = self.items.get(key)
        if not item:
            return
        if pages is not None:
            item.pages = pages
        if status is not None:
            item.status = status
        if error is not None:
            item.error = error
        self.refresh()

    def update_by_filename(self, filename: str, *, pages: int | None = None, status: str | None = None, error: str | None = None) -> None:
        for item in self.items.values():
            if item.path.name == filename:
                self.update_item(item.key, pages=pages, status=status, error=error)
                return

    def refresh(self) -> None:
        for child in self.rows.winfo_children():
            child.destroy()
        self._row_widgets.clear()
        if not self.items:
            self.empty_label = tk.Label(
                self.rows,
                text="Belum ada file PDF. Pilih file untuk mulai mengubah.",
                bg=PANEL,
                fg=SUBTLE,
                font=FONT,
                pady=32,
            )
            self.empty_label.pack(fill="x")
            return
        for index, item in enumerate(self.items.values()):
            self._create_row(item, index)

    def _create_row(self, item: PdfQueueItem, index: int) -> None:
        bg = PANEL if index % 2 == 0 else "#121b2d"
        row = tk.Frame(self.rows, bg=bg, padx=12, pady=8)
        row.pack(fill="x")
        self._row_widgets[item.key] = row
        row.grid_columnconfigure(0, weight=3, minsize=240)
        row.grid_columnconfigure(1, weight=1, minsize=80)
        row.grid_columnconfigure(2, weight=1, minsize=80)
        row.grid_columnconfigure(3, weight=1, minsize=90)
        row.grid_columnconfigure(4, weight=0, minsize=70)

        name = item.path.name
        if item.error:
            name = f"{name}\n{item.error}"
        tk.Label(row, text=name, bg=bg, fg=TEXT, font=FONT_SMALL, anchor="w", justify="left", wraplength=360).grid(
            row=0, column=0, sticky="ew"
        )
        tk.Label(row, text=human_size(item.size_bytes), bg=bg, fg=MUTED, font=FONT_SMALL, anchor="w").grid(row=0, column=1, sticky="ew")
        pages = "-" if item.pages is None else str(item.pages)
        tk.Label(row, text=pages, bg=bg, fg=MUTED, font=FONT_SMALL, anchor="w").grid(row=0, column=2, sticky="ew")
        tk.Label(row, text=item.status, bg=bg, fg=self._status_color(item.status), font=FONT_SMALL, anchor="w").grid(
            row=0, column=3, sticky="ew"
        )
        tk.Button(
            row,
            text="Hapus",
            command=lambda key=item.key: self.remove_callback(key),
            bg="#334155",
            fg=TEXT,
            activebackground="#475569",
            activeforeground=TEXT,
            bd=0,
            padx=8,
            pady=5,
            font=FONT_SMALL,
            cursor="hand2",
        ).grid(row=0, column=4, sticky="e")

    @staticmethod
    def _status_color(status: str) -> str:
        if status == "Selesai":
            return "#86efac"
        if status == "Gagal":
            return "#fca5a5"
        if status == "Diproses":
            return "#93c5fd"
        return MUTED

    def valid_items(self) -> list[PdfQueueItem]:
        return [item for item in self.items.values() if item.status != "Gagal"]

    def total_pages(self) -> int:
        return sum(item.pages or 0 for item in self.items.values())
