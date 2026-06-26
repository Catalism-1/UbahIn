from __future__ import annotations

from tkinter import ttk

BG = "#0f172a"
PANEL = "#162033"
PANEL_2 = "#1e293b"
TEXT = "#f8fafc"
MUTED = "#cbd5e1"
SUBTLE = "#94a3b8"
PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
DANGER = "#dc2626"
BORDER = "#334155"

FONT = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 24, "bold")
FONT_SECTION = ("Segoe UI", 14, "bold")


def configure_ttk() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Ubahin.Horizontal.TProgressbar", troughcolor=PANEL_2, background=PRIMARY, bordercolor=PANEL_2, lightcolor=PRIMARY)
    style.configure("Treeview", background=PANEL_2, foreground=TEXT, fieldbackground=PANEL_2, bordercolor=BORDER, rowheight=28)
    style.configure("Treeview.Heading", background=PANEL, foreground=TEXT, relief="flat")
