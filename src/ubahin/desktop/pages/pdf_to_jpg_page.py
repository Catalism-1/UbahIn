from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable

from ubahin.converter import PdfReadError, inspect_pdf
from ubahin.desktop.theme import FONT, FONT_SECTION, FONT_SMALL, MUTED, PANEL, PRIMARY, TEXT
from ubahin.desktop.widgets.file_queue import FileQueue, PdfQueueItem
from ubahin.desktop.widgets.progress_panel import ProgressPanel
from ubahin.desktop.widgets.settings_panel import SettingsPanel
from ubahin.events import AppEvent
from ubahin.manager import ConversionManager
from ubahin.models import ConversionOptions, PerformanceMode, QualityPreset
from ubahin.utils import get_log_dir, get_logger, open_in_file_manager, setup_logging

MAX_FILES = 50
LOGGER = get_logger("ubahin.desktop.pdf_to_jpg")


@dataclass(slots=True)
class ConversionRequest:
    input_paths: list[Path]
    output_dir: Path
    quality_preset: QualityPreset
    dpi: int
    jpeg_quality: int
    create_zip: bool
    open_after_finish: bool
    optimize_file_size: bool


class PdfToJpgPage(tk.Frame):
    def __init__(self, master: tk.Misc, status_callback: Callable[[str], None]) -> None:
        super().__init__(master, bg="#0f172a")
        self.status_callback = status_callback
        self.items: list[PdfQueueItem] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.manager: ConversionManager | None = None
        self.job_id: str | None = None
        self.is_running = False
        self.cancel_requested = False
        self.started_at = 0.0
        self.completed_files = 0
        self.open_after_finish = False
        self.main_thread_id = threading.get_ident()
        self._closed = False
        self._poll_after_id: str | None = None
        self._build()
        self._poll_after_id = self.after(100, self._drain_events)

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        title_row = tk.Frame(self, bg="#0f172a")
        title_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        tk.Label(title_row, text="PDF ke JPG", bg="#0f172a", fg=TEXT, font=FONT_SECTION).pack(side="left")
        tk.Label(
            title_row,
            text="Ubah setiap halaman PDF menjadi gambar JPG.",
            bg="#0f172a",
            fg=MUTED,
            font=FONT,
        ).pack(side="left", padx=(14, 0), pady=(4, 0))

        action_row = tk.Frame(self, bg="#0f172a")
        action_row.grid(row=0, column=1, sticky="e", pady=(0, 14))
        self.pick_button = tk.Button(
            action_row,
            text="Pilih File PDF",
            command=self.pick_files,
            bg=PRIMARY,
            fg=TEXT,
            activebackground="#1d4ed8",
            activeforeground=TEXT,
            bd=0,
            padx=14,
            pady=10,
            font=FONT_SMALL,
            cursor="hand2",
        )
        self.pick_button.pack(side="left")
        self.clear_button = tk.Button(
            action_row,
            text="Hapus Semua",
            command=self.clear_files,
            bg="#334155",
            fg=TEXT,
            activebackground="#475569",
            activeforeground=TEXT,
            bd=0,
            padx=14,
            pady=10,
            font=FONT_SMALL,
            cursor="hand2",
        )
        self.clear_button.pack(side="left", padx=(8, 0))

        main = tk.Frame(self, bg="#0f172a")
        main.grid(row=1, column=0, columnspan=2, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)

        self.file_queue = FileQueue(main, remove_callback=self.remove_file)
        self.file_queue.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        self.settings = SettingsPanel(main, change_callback=self.refresh_state)
        self.settings.grid(row=0, column=1, sticky="ns")
        self.settings.start_button.configure(command=self.start_conversion)

        bottom = tk.Frame(self, bg="#0f172a")
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        bottom.grid_columnconfigure(0, weight=1)
        self.progress = ProgressPanel(bottom)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.cancel_button = tk.Button(
            bottom,
            text="Batalkan Proses",
            command=self.cancel_conversion,
            state="disabled",
            bg="#7f1d1d",
            fg=TEXT,
            disabledforeground="#94a3b8",
            activebackground="#991b1b",
            activeforeground=TEXT,
            bd=0,
            padx=14,
            pady=12,
            font=FONT_SMALL,
            cursor="hand2",
        )
        self.cancel_button.grid(row=0, column=1, sticky="se", padx=(12, 0))

    def pick_files(self) -> None:
        if self.is_running:
            messagebox.showinfo("Proses berjalan", "Tunggu proses selesai sebelum mengubah daftar file.")
            return

        selected = filedialog.askopenfilenames(
            title="Pilih File PDF",
            filetypes=[("File PDF", "*.pdf"), ("Semua file", "*.*")],
        )
        if not selected:
            return

        existing = {item.path.resolve() for item in self.items}
        new_paths: list[Path] = []
        for raw_path in selected:
            path = Path(raw_path).expanduser().resolve()
            if path in existing or path.suffix.lower() != ".pdf":
                continue
            new_paths.append(path)

        if len(self.items) + len(new_paths) > MAX_FILES:
            allowed = max(MAX_FILES - len(self.items), 0)
            new_paths = new_paths[:allowed]
            messagebox.showwarning("Batas file", "Maksimal 50 file PDF dalam satu antrean.")

        if not new_paths:
            self.refresh_state()
            return

        for path in new_paths:
            size = path.stat().st_size if path.exists() else 0
            self.items.append(PdfQueueItem(path=path, size_bytes=size, status="Memeriksa"))
        self.file_queue.set_items(self.items)
        self.refresh_state()
        threading.Thread(target=self._inspect_files, args=(new_paths,), daemon=True, name="ubahin-pdf-inspect").start()

    def _inspect_files(self, paths: list[Path]) -> None:
        for path in paths:
            try:
                inspection = inspect_pdf(path)
                self.events.put(("inspect_ok", (path, inspection.page_count, inspection.file_size)))
            except PdfReadError as exc:
                self.events.put(("inspect_failed", (path, str(exc))))
            except Exception as exc:
                self.events.put(("inspect_failed", (path, f"{type(exc).__name__}: {exc}")))

    def remove_file(self, key: str) -> None:
        if self.is_running:
            messagebox.showinfo("Proses berjalan", "Daftar file tidak dapat diubah saat proses berjalan.")
            return
        self.items = [item for item in self.items if item.key != key]
        self.file_queue.set_items(self.items)
        self.refresh_state()

    def clear_files(self) -> None:
        if self.is_running:
            messagebox.showinfo("Proses berjalan", "Daftar file tidak dapat dihapus saat proses berjalan.")
            return
        self.items.clear()
        self.file_queue.set_items(self.items)
        self.progress.reset()
        self.refresh_state()

    def refresh_state(self) -> None:
        file_count = len(self.items)
        total_pages = sum(item.pages or 0 for item in self.items)
        self.settings.update_summary(file_count, total_pages)
        output_dir = self.settings.output_path()
        has_valid_file = any(item.status != "Gagal" for item in self.items)
        all_checked = all(item.status != "Memeriksa" for item in self.items)
        output_ok = output_dir is not None and output_dir.exists() and output_dir.is_dir()
        self.settings.set_start_enabled(not self.is_running and has_valid_file and all_checked and output_ok)

    def start_conversion(self) -> None:
        if self.is_running:
            return
        output_dir = self.settings.output_path()
        if output_dir is None or not output_dir.exists() or not output_dir.is_dir():
            messagebox.showwarning("Folder output", "Pilih folder output yang valid terlebih dahulu.")
            return
        if not self._is_writable_dir(output_dir):
            messagebox.showwarning("Folder output", "Folder output tidak dapat ditulis.")
            return
        if not self.items:
            messagebox.showwarning("Belum ada PDF", "Pilih minimal satu file PDF.")
            return
        valid_items = [item for item in self.items if item.status != "Gagal"]
        if not valid_items:
            messagebox.showwarning("Belum ada PDF valid", "Tidak ada PDF valid yang bisa diproses.")
            return

        preset, dpi, quality, _label = self.settings.preset_values()
        request = ConversionRequest(
            input_paths=[item.path for item in valid_items],
            output_dir=output_dir,
            quality_preset=preset,
            dpi=dpi,
            jpeg_quality=quality,
            create_zip=self.settings.zip_var.get(),
            open_after_finish=self.settings.open_after_var.get(),
            optimize_file_size=self.settings.optimize_var.get(),
        )

        self.is_running = True
        self.cancel_requested = False
        self.manager = None
        self.job_id = None
        self.open_after_finish = request.open_after_finish
        self.started_at = time.monotonic()
        self.completed_files = 0
        self.progress.reset()
        self.progress.status_var.set("Menyiapkan job konversi...")
        self.status_callback("Menyiapkan konversi PDF ke JPG.")
        self._set_controls_running(True)
        for item in self.items:
            if item.status != "Gagal":
                item.status = "Siap"
                item.error = ""
        self.file_queue.set_items(self.items)

        thread = threading.Thread(target=self._run_conversion, args=(request,), daemon=True, name="ubahin-demo-convert")
        thread.start()

    def _run_conversion(self, request: ConversionRequest) -> None:
        try:
            setup_logging()
            LOGGER.info("Starting conversion worker thread=%s files=%s", threading.current_thread().name, len(request.input_paths))
            options = ConversionOptions(
                output_dir=request.output_dir,
                quality_preset=request.quality_preset,
                dpi=request.dpi,
                jpeg_quality=request.jpeg_quality,
                performance_mode=PerformanceMode.BALANCED,
                create_zip=request.create_zip,
                open_output_after_finish=False,
                optimize_file_size=request.optimize_file_size,
                max_files=MAX_FILES,
            )
            manager = ConversionManager()
            manager.add_listener(lambda event: self._queue_backend_event(event))
            job = manager.create_pdf_to_jpg_job(request.input_paths, options)
            self.manager = manager
            self.job_id = job.job_id
            self.events.put(("job_ready", job.job_id))
            manager.start(job.job_id)
        except Exception as exc:
            LOGGER.exception("Conversion worker failed before job start thread=%s", threading.current_thread().name)
            self.events.put(("conversion_error", {"message": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}))

    def cancel_conversion(self) -> None:
        self.cancel_requested = True
        if self.manager and self.job_id:
            self.manager.cancel(self.job_id)
        self.status_callback("Permintaan pembatalan dikirim.")
        self.progress.status_var.set("Membatalkan proses...")

    def _queue_backend_event(self, event: AppEvent) -> None:
        LOGGER.info("Queue UI event type=%s job_id=%s thread=%s", event.kind, event.job_id, threading.current_thread().name)
        self.events.put(("backend_event", event))

    def _drain_events(self) -> None:
        if self._closed:
            return
        self._assert_main_thread("_drain_events")
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(kind, payload)
        self._poll_after_id = self.after(100, self._drain_events)

    def _handle_event(self, kind: str, payload: object) -> None:
        self._assert_main_thread(f"_handle_event:{kind}")
        if kind == "inspect_ok":
            path, pages, size = payload  # type: ignore[misc]
            self._update_item(Path(path), pages=int(pages), size_bytes=int(size), status="Siap", error="")
        elif kind == "inspect_failed":
            path, error = payload  # type: ignore[misc]
            self._update_item(Path(path), status="Gagal", error=str(error))
        elif kind == "backend_event":
            self._handle_backend_event(payload)  # type: ignore[arg-type]
        elif kind == "conversion_error":
            message = str(payload.get("message", payload)) if isinstance(payload, dict) else str(payload)
            self._finish_after_error(message)
        elif kind == "job_ready":
            self.job_id = str(payload)
            if self.cancel_requested and self.manager:
                self.manager.cancel(self.job_id)
        self.refresh_state()

    def _handle_backend_event(self, event: AppEvent) -> None:
        self._assert_main_thread(f"backend_event:{event.kind}")
        payload = event.payload
        if event.kind == "file_analyzed":
            self.file_queue.update_by_filename(
                str(payload.get("filename", "")),
                pages=int(payload.get("pages_total") or 0),
                status="Siap",
                error="",
            )
        elif event.kind == "job_started":
            self.status_callback("Konversi berjalan.")
            self.progress.status_var.set("Konversi berjalan...")
        elif event.kind == "file_progress":
            filename = str(payload.get("filename", ""))
            self.file_queue.update_by_filename(filename, status="Diproses")
            completed_pages = int(payload.get("completed_pages") or 0)
            total_pages = int(payload.get("total_pages") or 0)
            file_done = int(payload.get("file_pages_done") or 0)
            file_total = int(payload.get("file_pages_total") or 0)
            self.progress.set_progress(
                filename=filename,
                file_done=file_done,
                file_total=file_total,
                completed_pages=completed_pages,
                total_pages=total_pages,
                completed_files=self.completed_files,
                total_files=len(self.items),
                status="Sedang membuat JPG...",
            )
        elif event.kind == "file_completed":
            filename = str(payload.get("filename", ""))
            output_count = int(payload.get("output_count") or 0)
            self.completed_files += 1
            self.file_queue.update_by_filename(filename, status="Selesai", error=f"{output_count} JPG dibuat")
        elif event.kind == "file_failed":
            filename = str(payload.get("filename", ""))
            self.file_queue.update_by_filename(filename, status="Gagal", error=str(payload.get("error", "")))
        elif event.kind == "file_cancelled":
            filename = str(payload.get("filename", ""))
            self.file_queue.update_by_filename(filename, status="Gagal", error="Dibatalkan")
        elif event.kind == "zip_created":
            self.progress.status_var.set(f"ZIP dibuat: {Path(str(payload.get('zip_path'))).name}")
        elif event.kind == "job_cancellation_requested":
            self.progress.status_var.set("Membatalkan proses...")
        elif event.kind == "job_error":
            self.progress.status_var.set("Terjadi kesalahan. Detail tersimpan di log.")
            self.status_callback(str(payload.get("error", "Konversi gagal.")))
        elif event.kind == "job_finished":
            job = payload.get("job")
            if isinstance(job, dict):
                self._finish_job(job)

    def _update_item(
        self,
        path: Path,
        *,
        pages: int | None = None,
        size_bytes: int | None = None,
        status: str | None = None,
        error: str | None = None,
    ) -> None:
        for item in self.items:
            if item.path == path:
                if pages is not None:
                    item.pages = pages
                if size_bytes is not None:
                    item.size_bytes = size_bytes
                if status is not None:
                    item.status = status
                if error is not None:
                    item.error = error
                break
        self.file_queue.set_items(self.items)

    def _finish_after_error(self, message: str) -> None:
        self.is_running = False
        self._set_controls_running(False)
        self.progress.status_var.set("Konversi gagal sebelum dimulai.")
        self.status_callback("Konversi gagal. Detail teknis tersimpan di log.")
        LOGGER.error("Conversion failed before start: %s", message)
        messagebox.showerror(
            "Konversi gagal",
            "Konversi gagal dijalankan. Silakan buka log untuk melihat detail.",
        )

    def _finish_job(self, job: dict[str, Any]) -> None:
        self.is_running = False
        self._set_controls_running(False)
        summary = job.get("summary", {})
        total_pages = int(summary.get("total_pages") or 0)
        completed_pages = int(summary.get("completed_pages") or 0)
        success = int(summary.get("success_count") or 0)
        status = str(job.get("status", ""))
        if status == "cancelled":
            self.progress.status_var.set("Proses dibatalkan. File yang sudah selesai tetap tersimpan.")
            self.status_callback("Proses dibatalkan.")
        else:
            self.progress.status_var.set("Konversi selesai.")
            self.status_callback("Konversi selesai.")
        self.progress.overall_var.set(100 if total_pages and completed_pages >= total_pages else self.progress.overall_var.get())
        if self.open_after_finish and status in {"completed", "completed_with_errors"}:
            output_dir = Path(str(job.get("options", {}).get("output_dir", "")))
            self._open_path(output_dir)
        try:
            self.winfo_toplevel().bell()
        except tk.TclError:
            pass
        self._show_result_dialog(job, success)

    def _set_controls_running(self, running: bool) -> None:
        self._assert_main_thread("_set_controls_running")
        state = "disabled" if running else "normal"
        self.pick_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.cancel_button.configure(state="normal" if running else "disabled")
        self.settings.set_start_enabled(False if running else True)
        if not running:
            self.refresh_state()

    def _show_result_dialog(self, job: dict[str, Any], success: int) -> None:
        summary = job.get("summary", {})
        options = job.get("options", {})
        tasks = job.get("tasks", [])
        output_dir = Path(str(options.get("output_dir", "")))
        failed_tasks = [task for task in tasks if str(task.get("status")) in {"failed", "cancelled"}]
        duration = time.monotonic() - self.started_at if self.started_at else 0

        dialog = tk.Toplevel(self)
        dialog.title("Konversi Selesai")
        dialog.geometry("520x430")
        dialog.configure(bg=PANEL)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        tk.Label(dialog, text="Konversi Selesai", bg=PANEL, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(18, 8))
        body = tk.Frame(dialog, bg=PANEL, padx=20)
        body.pack(fill="both", expand=True)
        lines = [
            f"File berhasil: {success}",
            f"File gagal: {int(summary.get('failure_count') or 0) + int(summary.get('cancelled_count') or 0)}",
            f"Total JPG dibuat: {int(summary.get('total_output_files') or 0)}",
            f"Durasi proses: {duration:.1f} detik",
            f"Lokasi output: {output_dir}",
        ]
        for line in lines:
            tk.Label(body, text=line, bg=PANEL, fg=TEXT, font=FONT_SMALL, anchor="w", justify="left", wraplength=470).pack(
                anchor="w", pady=3
            )

        if failed_tasks:
            names = ", ".join(str(task.get("source_path", "")).split("\\")[-1] for task in failed_tasks[:4])
            if len(failed_tasks) > 4:
                names = f"{names}, ..."
            tk.Label(
                body,
                text=f"File gagal: {names}",
                bg=PANEL,
                fg="#fca5a5",
                font=FONT_SMALL,
                anchor="w",
                justify="left",
                wraplength=470,
            ).pack(anchor="w", pady=(12, 4))

        buttons = tk.Frame(dialog, bg=PANEL, padx=20, pady=16)
        buttons.pack(fill="x")
        self._dialog_button(buttons, "Buka Folder Hasil", lambda: self._open_path(output_dir)).pack(side="left", padx=(0, 8))
        if failed_tasks:
            self._dialog_button(buttons, "Buka Log", lambda: self._open_path(get_log_dir())).pack(side="left", padx=(0, 8))
        self._dialog_button(buttons, "Konversi Lagi", lambda: self._convert_again(dialog)).pack(side="right", padx=(8, 0))
        self._dialog_button(buttons, "Tutup", dialog.destroy).pack(side="right")

    @staticmethod
    def _dialog_button(parent: tk.Misc, text: str, command: Callable[[], None]) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#334155",
            fg=TEXT,
            activebackground="#475569",
            activeforeground=TEXT,
            bd=0,
            padx=12,
            pady=8,
            font=FONT_SMALL,
            cursor="hand2",
        )

    def _open_path(self, path: Path) -> None:
        try:
            open_in_file_manager(path)
        except OSError as exc:
            messagebox.showerror("Tidak dapat membuka folder", str(exc))

    def _convert_again(self, dialog: tk.Toplevel) -> None:
        dialog.destroy()
        for item in self.items:
            if item.status in {"Selesai", "Gagal", "Diproses"}:
                item.status = "Siap" if item.pages else "Gagal"
                if item.status == "Siap":
                    item.error = ""
        self.file_queue.set_items(self.items)
        self.progress.reset()
        self.refresh_state()

    @staticmethod
    def _is_writable_dir(path: Path) -> bool:
        try:
            probe = path / ".ubahin_write_test.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def _assert_main_thread(self, action: str) -> None:
        if threading.get_ident() != self.main_thread_id:
            LOGGER.error(
                "Unsafe Tk access detected action=%s current_thread=%s main_thread_id=%s",
                action,
                threading.current_thread().name,
                self.main_thread_id,
            )

    def destroy(self) -> None:
        self._closed = True
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        super().destroy()
