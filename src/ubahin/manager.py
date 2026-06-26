from __future__ import annotations

import logging
import os
import threading
import time
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .converter import PdfReadError, convert_pdf_to_jpg, inspect_pdf
from .events import AppEvent, EventListener
from .history import HistoryStore
from .models import (
    ConversionJob,
    ConversionOptions,
    FileTask,
    JobStatus,
    PerformanceMode,
    TaskStatus,
)
from .utils import available_disk_bytes, coerce_pdf_paths, estimated_output_bytes, open_in_file_manager, unique_file

LOGGER = logging.getLogger("ubahin")


@dataclass(slots=True)
class JobRuntime:
    cancel_event: threading.Event
    thread: threading.Thread | None = None
    started_monotonic: float = 0.0


class ConversionManager:
    """Backend yang dapat dipanggil GUI apa pun: Tkinter, CustomTkinter, Flet, atau Qt."""

    def __init__(self, history_store: HistoryStore | None = None) -> None:
        self.history_store = history_store or HistoryStore()
        self._jobs: dict[str, ConversionJob] = {}
        self._runtime: dict[str, JobRuntime] = {}
        self._listeners: list[EventListener] = []
        self._lock = threading.RLock()

    def add_listener(self, listener: EventListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: EventListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _emit(self, kind: str, job_id: str, **payload: object) -> None:
        event = AppEvent(kind=kind, job_id=job_id, payload=dict(payload))
        for listener in tuple(self._listeners):
            try:
                listener(event)
            except Exception:  # GUI listener tidak boleh menjatuhkan mesin konversi.
                LOGGER.exception("Listener event gagal")

    def create_pdf_to_jpg_job(
        self,
        paths: Iterable[str | Path],
        options: ConversionOptions,
    ) -> ConversionJob:
        pdf_paths = coerce_pdf_paths(paths)
        if not pdf_paths:
            raise ValueError("Pilih minimal satu file PDF.")
        if len(pdf_paths) > options.max_files:
            raise ValueError(f"Maksimal {options.max_files} file PDF dalam satu kali proses.")

        options.output_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(options.output_dir, os.W_OK):
            raise PermissionError("Folder hasil tidak dapat ditulis.")

        tasks = [FileTask(source_path=path, status=TaskStatus.ANALYZING) for path in pdf_paths]
        job = ConversionJob(tasks=tasks, options=options)
        self._emit("job_created", job.job_id, total_files=len(tasks))

        for task in tasks:
            try:
                inspection = inspect_pdf(task.source_path)
                task.pages_total = inspection.page_count
                task.status = TaskStatus.READY
                self._emit(
                    "file_analyzed",
                    job.job_id,
                    task_id=task.task_id,
                    filename=task.filename,
                    pages_total=task.pages_total,
                    file_size=inspection.file_size,
                )
            except PdfReadError as exc:
                task.status = TaskStatus.FAILED
                task.error_message = str(exc)
                self._emit(
                    "file_failed",
                    job.job_id,
                    task_id=task.task_id,
                    filename=task.filename,
                    error=task.error_message,
                )

        estimate = estimated_output_bytes(job.total_pages, options.dpi, options.jpeg_quality)
        free_space = available_disk_bytes(options.output_dir)
        if job.total_pages > 0 and free_space < max(estimate, 20 * 1024 * 1024):
            raise OSError(
                "Ruang penyimpanan tidak cukup untuk perkiraan hasil konversi. "
                f"Tersedia {free_space // (1024 * 1024)} MB."
            )

        with self._lock:
            self._jobs[job.job_id] = job
            self._runtime[job.job_id] = JobRuntime(cancel_event=threading.Event())
        return job

    def start(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            runtime = self._runtime[job_id]
            if runtime.thread and runtime.thread.is_alive():
                raise RuntimeError("Proses konversi sudah berjalan.")
            runtime.thread = threading.Thread(
                target=self._run_job,
                args=(job_id,),
                daemon=True,
                name=f"ubahin-job-{job_id[:8]}",
            )
            runtime.thread.start()

    def wait(self, job_id: str, timeout: float | None = None) -> bool:
        runtime = self._runtime[job_id]
        if not runtime.thread:
            return True
        runtime.thread.join(timeout)
        return not runtime.thread.is_alive()

    def cancel(self, job_id: str) -> None:
        with self._lock:
            runtime = self._runtime[job_id]
            runtime.cancel_event.set()
        self._emit("job_cancellation_requested", job_id)

    def get_job(self, job_id: str) -> ConversionJob:
        return self._jobs[job_id]

    def open_result_folder(self, job_id: str) -> None:
        job = self._jobs[job_id]
        open_in_file_manager(job.options.output_dir)

    @staticmethod
    def _worker_count(mode: PerformanceMode) -> int:
        cpu = os.cpu_count() or 2
        if mode == PerformanceMode.RAM_SAVER:
            return 1
        if mode == PerformanceMode.FAST:
            return min(4, max(2, cpu - 1))
        return min(2, max(1, cpu - 1))

    def _run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        runtime = self._runtime[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        runtime.started_monotonic = time.monotonic()
        self._emit("job_started", job_id, total_files=len(job.tasks), total_pages=job.total_pages)

        ready_tasks = [task for task in job.tasks if task.status == TaskStatus.READY]
        if not ready_tasks:
            job.status = JobStatus.FAILED
            job.error_message = "Tidak ada PDF valid yang dapat diproses."
            job.finished_at = datetime.now(timezone.utc)
            self.history_store.save(job)
            self._emit("job_finished", job_id, job=job.to_dict())
            return

        def on_page_progress(task: FileTask) -> None:
            elapsed = max(time.monotonic() - runtime.started_monotonic, 0.001)
            completed = job.completed_pages
            rate = completed / elapsed
            remaining = max(job.total_pages - completed, 0)
            eta_seconds = int(remaining / rate) if rate else None
            self._emit(
                "file_progress",
                job_id,
                task_id=task.task_id,
                filename=task.filename,
                file_pages_done=task.pages_done,
                file_pages_total=task.pages_total,
                completed_pages=completed,
                total_pages=job.total_pages,
                eta_seconds=eta_seconds,
            )

        def on_message(kind: str, payload: dict[str, object]) -> None:
            self._emit(kind, job_id, **payload)

        workers = self._worker_count(job.options.performance_mode)
        futures: dict[Future[FileTask], FileTask] = {}
        try:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ubahin-pdf") as executor:
                for task in ready_tasks:
                    if runtime.cancel_event.is_set():
                        task.status = TaskStatus.CANCELLED
                        continue
                    task.started_at = datetime.now(timezone.utc)
                    futures[executor.submit(
                        convert_pdf_to_jpg,
                        task,
                        job.options,
                        runtime.cancel_event,
                        on_page_progress,
                        on_message,
                    )] = task

                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        result.finished_at = datetime.now(timezone.utc)
                        if result.status == TaskStatus.COMPLETED:
                            self._emit(
                                "file_completed",
                                job_id,
                                task_id=result.task_id,
                                filename=result.filename,
                                output_dir=str(result.output_dir) if result.output_dir else None,
                                output_count=len(result.output_files),
                            )
                        elif result.status == TaskStatus.CANCELLED:
                            self._emit("file_cancelled", job_id, task_id=result.task_id, filename=result.filename)
                        else:
                            self._emit(
                                "file_failed",
                                job_id,
                                task_id=result.task_id,
                                filename=result.filename,
                                error=result.error_message or "Terjadi kesalahan tidak diketahui.",
                            )
                    except Exception as exc:
                        task.status = TaskStatus.FAILED
                        task.error_message = f"Kesalahan tidak terduga: {exc}"
                        task.finished_at = datetime.now(timezone.utc)
                        LOGGER.exception("PDF gagal diproses: %s", task.filename)
                        self._emit("file_failed", job_id, task_id=task.task_id, filename=task.filename, error=task.error_message)

            if runtime.cancel_event.is_set():
                for task in job.tasks:
                    if task.status in {TaskStatus.QUEUED, TaskStatus.READY, TaskStatus.ANALYZING}:
                        task.status = TaskStatus.CANCELLED
                job.status = JobStatus.CANCELLED
            elif job.failure_count > 0:
                job.status = JobStatus.COMPLETED_WITH_ERRORS
            else:
                job.status = JobStatus.COMPLETED

            if job.options.create_zip and job.status in {JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS} and job.total_output_files:
                job.zip_path = self._create_zip(job)
                self._emit("zip_created", job_id, zip_path=str(job.zip_path))
        except Exception as exc:
            LOGGER.exception("Job gagal")
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            self._emit("job_error", job_id, error=str(exc))
        finally:
            job.finished_at = datetime.now(timezone.utc)
            self.history_store.save(job)
            self._emit("job_finished", job_id, job=job.to_dict())
            if job.options.open_output_after_finish and job.status in {JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS}:
                try:
                    open_in_file_manager(job.options.output_dir)
                except OSError:
                    LOGGER.warning("Folder hasil tidak dapat dibuka otomatis")

    def _create_zip(self, job: ConversionJob) -> Path:
        zip_path = unique_file(job.options.output_dir, "Ubahin_Hasil.zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for task in job.tasks:
                for file_path in task.output_files:
                    try:
                        archive.write(file_path, file_path.relative_to(job.options.output_dir))
                    except FileNotFoundError:
                        LOGGER.warning("Melewati output yang hilang: %s", file_path)
        return zip_path
