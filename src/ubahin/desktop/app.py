from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import messagebox

from ubahin.desktop.self_check import format_report, run_self_check
from ubahin.desktop.self_check import main as self_check_main
from ubahin.desktop.startup import show_startup_error_dialog, write_startup_exception
from ubahin.native_bridge import native_status
from ubahin.utils import get_app_data_dir, get_log_dir, setup_logging


def _open_log_folder() -> None:
    log_dir = get_log_dir()
    try:
        if sys.platform == "win32":
            os.startfile(log_dir)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("Folder log", str(log_dir))
    except Exception as exc:
        messagebox.showerror("Gagal membuka folder log", str(exc))


def _native_text() -> str:
    status = native_status()
    if status.get("available"):
        return "Akselerasi native: Aktif"
    return "Akselerasi native: Tidak aktif - mode standar tetap berjalan."


def _run_window_self_check(status_var: tk.StringVar) -> None:
    try:
        report = run_self_check()
        status_var.set("Status engine: OK" if report.ok else "Status engine: Perlu perhatian")
        if report.ok:
            messagebox.showinfo("Pemeriksaan Sistem", format_report(report))
        else:
            messagebox.showwarning("Pemeriksaan Sistem", format_report(report))
    except Exception as exc:
        log_path = write_startup_exception(exc)
        status_var.set("Status engine: Gagal menjalankan pemeriksaan")
        messagebox.showerror(
            "Pemeriksaan gagal",
            "Pemeriksaan sistem gagal. Detail teknis telah disimpan di folder log.\n\n"
            f"Lokasi log:\n{log_path}",
        )


def launch_desktop_shell() -> int:
    setup_logging()
    app_dir = get_app_data_dir()
    log_dir = get_log_dir()
    root = tk.Tk()
    root.title("Ubahin")
    root.geometry("560x390")
    root.minsize(520, 360)
    root.configure(bg="#141821")

    status_var = tk.StringVar(value="Status engine: Siap")

    container = tk.Frame(root, bg="#141821", padx=28, pady=24)
    container.pack(fill="both", expand=True)

    title = tk.Label(container, text="Ubahin", fg="#f8fafc", bg="#141821", font=("Segoe UI", 28, "bold"))
    title.pack(anchor="w")

    subtitle = tk.Label(
        container,
        text="Ubah file jadi lebih mudah.",
        fg="#cbd5e1",
        bg="#141821",
        font=("Segoe UI", 12),
    )
    subtitle.pack(anchor="w", pady=(2, 18))

    info_frame = tk.Frame(container, bg="#1f2937", padx=16, pady=14)
    info_frame.pack(fill="x", pady=(0, 18))

    rows = [
        status_var.get(),
        _native_text(),
        f"App data: {app_dir}",
        f"Log: {log_dir}",
    ]
    for text in rows:
        if text == rows[0]:
            label = tk.Label(info_frame, textvariable=status_var, fg="#e2e8f0", bg="#1f2937", anchor="w", font=("Segoe UI", 10))
        else:
            label = tk.Label(info_frame, text=text, fg="#e2e8f0", bg="#1f2937", anchor="w", justify="left", wraplength=480, font=("Segoe UI", 10))
        label.pack(fill="x", anchor="w", pady=2)

    button_frame = tk.Frame(container, bg="#141821")
    button_frame.pack(fill="x", pady=(4, 0))

    button_style = {"font": ("Segoe UI", 10), "height": 2, "bd": 0, "relief": "flat", "cursor": "hand2"}

    check_button = tk.Button(
        button_frame,
        text="Jalankan Pemeriksaan Sistem",
        command=lambda: _run_window_self_check(status_var),
        bg="#2563eb",
        fg="#ffffff",
        activebackground="#1d4ed8",
        activeforeground="#ffffff",
        **button_style,
    )
    check_button.pack(fill="x", pady=4)

    log_button = tk.Button(
        button_frame,
        text="Buka Folder Log",
        command=_open_log_folder,
        bg="#334155",
        fg="#ffffff",
        activebackground="#475569",
        activeforeground="#ffffff",
        **button_style,
    )
    log_button.pack(fill="x", pady=4)

    close_button = tk.Button(
        button_frame,
        text="Tutup",
        command=root.destroy,
        bg="#475569",
        fg="#ffffff",
        activebackground="#64748b",
        activeforeground="#ffffff",
        **button_style,
    )
    close_button.pack(fill="x", pady=4)

    root.mainloop()
    return 0


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Ubahin", description="Launcher desktop Ubahin")
    parser.add_argument("--self-check", action="store_true", help="Jalankan pemeriksaan sistem internal.")
    parser.add_argument("--silent", action="store_true", help="Mode non-interaktif untuk pemeriksaan/build.")
    parser.add_argument("--json", action="store_true", help="Cetak laporan self-check dalam JSON.")
    args = parser.parse_args(argv)

    if args.self_check:
        self_args: list[str] = []
        if args.silent:
            self_args.append("--silent")
        if args.json:
            self_args.append("--json")
        return self_check_main(self_args)
    return launch_desktop_shell()


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(sys.argv[1:] if argv is None else argv)
    except SystemExit:
        raise
    except Exception as exc:
        log_path = write_startup_exception(exc)
        if argv is None and "--silent" not in sys.argv:
            show_startup_error_dialog(log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
