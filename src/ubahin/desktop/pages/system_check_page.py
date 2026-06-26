from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Callable

from ubahin.desktop.self_check import format_report, run_self_check
from ubahin.desktop.theme import BORDER, FONT, FONT_SECTION, FONT_SMALL, MUTED, PANEL, PANEL_2, PRIMARY, TEXT
from ubahin.native_bridge import native_status
from ubahin.utils import get_app_data_dir, get_log_dir, open_in_file_manager


class SystemCheckPage(tk.Frame):
    def __init__(self, master: tk.Misc, status_callback: Callable[[str], None]) -> None:
        super().__init__(master, bg="#0f172a")
        self.status_callback = status_callback
        self.events: queue.Queue[str] = queue.Queue()
        self.report_var = tk.StringVar(value="Klik tombol pemeriksaan untuk melihat status dependency.")
        self._closed = False
        self._poll_after_id: str | None = None
        self._build()
        self._set_initial_report()
        self._poll_after_id = self.after(120, self._poll_events)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        tk.Label(self, text="Pemeriksaan Sistem", bg="#0f172a", fg=TEXT, font=FONT_SECTION).grid(row=0, column=0, sticky="w")
        tk.Label(
            self,
            text="Cek kesiapan dependency, folder data aplikasi, dan status akselerasi native.",
            bg="#0f172a",
            fg=MUTED,
            font=FONT,
        ).grid(row=1, column=0, sticky="w", pady=(6, 16))

        card = tk.Frame(self, bg=PANEL, padx=16, pady=16, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=2, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        info = tk.Frame(card, bg=PANEL_2, padx=12, pady=12)
        info.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        native = native_status()
        native_text = "Aktif" if native.get("available") else "Tidak aktif - mode standar tetap berjalan."
        rows = [
            ("Status engine", "Siap"),
            ("Akselerasi native", native_text),
            ("App data", str(get_app_data_dir())),
            ("Log", str(get_log_dir())),
        ]
        for label, value in rows:
            row = tk.Frame(info, bg=PANEL_2)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", bg=PANEL_2, fg=MUTED, font=FONT_SMALL, width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=PANEL_2, fg=TEXT, font=FONT_SMALL, anchor="w", justify="left", wraplength=760).pack(
                side="left", fill="x", expand=True
            )

        self.text = tk.Text(card, bg="#0b1220", fg=TEXT, insertbackground=TEXT, bd=0, font=("Consolas", 9), wrap="word")
        self.text.grid(row=1, column=0, sticky="nsew")
        self.text.configure(state="disabled")

        buttons = tk.Frame(card, bg=PANEL, pady=12)
        buttons.grid(row=2, column=0, sticky="ew")
        tk.Button(
            buttons,
            text="Jalankan Self-check",
            command=self.run_check,
            bg=PRIMARY,
            fg=TEXT,
            activebackground="#1d4ed8",
            activeforeground=TEXT,
            bd=0,
            padx=12,
            pady=9,
            font=FONT_SMALL,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            buttons,
            text="Buka Folder Log",
            command=lambda: open_in_file_manager(get_log_dir()),
            bg="#334155",
            fg=TEXT,
            activebackground="#475569",
            activeforeground=TEXT,
            bd=0,
            padx=12,
            pady=9,
            font=FONT_SMALL,
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

    def _set_initial_report(self) -> None:
        native = native_status()
        text = "\n".join(
            [
                "Pemeriksaan belum dijalankan.",
                "",
                f"App data: {get_app_data_dir()}",
                f"Log: {get_log_dir()}",
                f"Native: {'aktif' if native.get('available') else 'fallback Python'} ({native.get('backend')})",
            ]
        )
        self._write_text(text)

    def run_check(self) -> None:
        self.status_callback("Menjalankan pemeriksaan sistem...")
        self._write_text("Pemeriksaan sedang berjalan...")
        threading.Thread(target=self._run_check_worker, daemon=True, name="ubahin-self-check-ui").start()

    def _run_check_worker(self) -> None:
        try:
            report = run_self_check()
            text = format_report(report)
        except Exception as exc:
            text = f"Pemeriksaan gagal: {type(exc).__name__}: {exc}"
        self.events.put(text)

    def _poll_events(self) -> None:
        if self._closed:
            return
        while True:
            try:
                text = self.events.get_nowait()
            except queue.Empty:
                break
            self._show_report(text)
        self._poll_after_id = self.after(120, self._poll_events)

    def _show_report(self, text: str) -> None:
        self._write_text(text)
        self.status_callback("Pemeriksaan sistem selesai.")

    def _write_text(self, text: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.configure(state="disabled")

    def destroy(self) -> None:
        self._closed = True
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        super().destroy()
