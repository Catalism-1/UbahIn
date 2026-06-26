from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from ubahin.core.job import Job
from ubahin.core.models import AppError, JobOptions, JobStatus, ServiceResult, ToolType, utc_now
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_image_batch, validate_output_dir, validate_pdf_batch, validate_pdf_file
from ubahin.services import (
    CompressPdfOptions,
    CompressPdfService,
    HistoryService,
    ImageCompressOptions,
    ImageCompressService,
    ImageConvertOptions,
    ImageConvertService,
    ImageResizeOptions,
    ImageResizeService,
    ImageToPdfOptions,
    ImageToPdfService,
    MergePdfOptions,
    MergePdfService,
    PdfToImageOptions,
    PdfToImageService,
    SplitPdfOptions,
    SplitPdfService,
    ZipService,
)
from ubahin.utils import get_logger


class JobManager:
    def __init__(self, history_service: HistoryService | None = None) -> None:
        self.history_service = history_service or HistoryService()
        self._jobs: dict[str, Job] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        self._callbacks: dict[str, list[Callable[..., None]]] = {
            "on_job_started": [],
            "on_progress": [],
            "on_file_completed": [],
            "on_job_completed": [],
            "on_job_failed": [],
            "on_job_cancelled": [],
        }
        self.logger = get_logger("ubahin.job_manager")

    def add_callback(self, event_name: str, callback: Callable[..., None]) -> None:
        if event_name not in self._callbacks:
            raise ValueError(f"Event tidak dikenal: {event_name}")
        self._callbacks[event_name].append(callback)

    def _emit(self, event_name: str, *args: object) -> None:
        for callback in tuple(self._callbacks.get(event_name, [])):
            try:
                callback(*args)
            except Exception:
                self.logger.exception("Callback gagal: %s", event_name)

    def create_job(self, tool_type: ToolType | str, input_files: list[str | Path], output_folder: str | Path, **params: object) -> Job:
        tool = ToolType(tool_type)
        performance = params.pop("performance_mode", "seimbang")
        options = JobOptions(
            output_dir=Path(output_folder),
            performance_mode=performance,  # type: ignore[arg-type]
            create_zip=bool(params.pop("create_zip", False)),
            params=dict(params),
        )
        job = Job(tool_type=tool, input_files=[Path(path).expanduser().resolve() for path in input_files], options=options)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def validate_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.VALIDATING
        validate_output_dir(job.options.output_dir)
        if job.tool_type == ToolType.PDF_TO_JPG:
            validate_pdf_batch(job.input_files, max_files=50)
        elif job.tool_type == ToolType.MERGE_PDF:
            validate_pdf_batch(job.input_files, max_files=999)
        elif job.tool_type in {ToolType.SPLIT_PDF, ToolType.COMPRESS_PDF}:
            if len(job.input_files) != 1:
                raise AppError("Fitur ini membutuhkan tepat satu file PDF.")
            validate_pdf_file(job.input_files[0])
        elif job.tool_type in {ToolType.IMAGE_TO_PDF, ToolType.IMAGE_CONVERT, ToolType.IMAGE_RESIZE, ToolType.IMAGE_COMPRESS}:
            validate_image_batch(job.input_files)
        job.status = JobStatus.PENDING

    def start_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job_id in self._threads and self._threads[job_id].is_alive():
                raise AppError("Job sudah berjalan.")
            thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True, name=f"ubahin-job-{job_id[:8]}")
            self._threads[job_id] = thread
            thread.start()

    def wait(self, job_id: str, timeout: float | None = None) -> bool:
        thread = self._threads.get(job_id)
        if not thread:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def cancel_job(self, job_id: str) -> None:
        self._jobs[job_id].cancellation_token.cancel()

    def get_job_status(self, job_id: str) -> JobStatus:
        return self._jobs[job_id].status

    def get_job_progress(self, job_id: str) -> ProgressInfo:
        return self._jobs[job_id].progress

    def get_job_result(self, job_id: str) -> ServiceResult | None:
        return self._jobs[job_id].result

    def get_job(self, job_id: str) -> Job:
        return self._jobs[job_id]

    def list_active_jobs(self) -> list[Job]:
        return [job for job in self._jobs.values() if job.status in {JobStatus.PENDING, JobStatus.VALIDATING, JobStatus.PROCESSING}]

    def list_history(self, limit: int = 50, status: str | None = None) -> list[dict[str, object]]:
        return self.history_service.list_recent(limit=limit, status=status)

    def clear_history(self) -> None:
        self.history_service.clear()

    def _run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        try:
            self.validate_job(job_id)
            job.status = JobStatus.PROCESSING
            job.start_time = utc_now()
            self._emit("on_job_started", job)
            result = self._execute(job)
            job.result = result
            if job.cancellation_token.is_cancelled():
                job.status = JobStatus.CANCELLED
                self._emit("on_job_cancelled", job)
            elif result.errors and not result.output_paths:
                job.status = JobStatus.FAILED
                job.errors.extend(result.errors)
                self._emit("on_job_failed", job)
            else:
                job.status = JobStatus.COMPLETED
                job.errors.extend(result.errors)
                self._emit("on_job_completed", job)
        except InterruptedError:
            job.status = JobStatus.CANCELLED
            self._emit("on_job_cancelled", job)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.errors.append(str(exc))
            self.logger.exception("Job gagal: %s", job_id)
            self._emit("on_job_failed", job)
        finally:
            job.end_time = utc_now()
            self._write_conversion_log(job)
            self.history_service.save_job(job)

    def _progress_callback(self, job: Job) -> Callable[[ProgressInfo], None]:
        def update(progress: ProgressInfo) -> None:
            job.progress = progress
            self._emit("on_progress", job, progress)

        return update

    def _execute(self, job: Job) -> ServiceResult:
        params = job.options.params
        progress = self._progress_callback(job)
        if job.tool_type == ToolType.PDF_TO_JPG:
            result = PdfToImageService().convert_to_jpg(
                job.input_files,
                PdfToImageOptions(
                    output_dir=job.options.output_dir,
                    dpi=int(params.get("dpi", 200)),
                    jpg_quality=int(params.get("jpg_quality", 90)),
                    preset=str(params.get("preset", "Tinggi")),
                    white_background=bool(params.get("white_background", True)),
                    optimize_size=bool(params.get("optimize_size", True)),
                ),
                job.cancellation_token,
                progress,
            )
        elif job.tool_type == ToolType.IMAGE_TO_PDF:
            result = ImageToPdfService().convert(
                job.input_files,
                ImageToPdfOptions(
                    output_dir=job.options.output_dir,
                    output_name=str(params.get("output_name", "hasil_gambar.pdf")),
                    page_size=str(params.get("page_size", "Original")),
                    orientation=str(params.get("orientation", "Otomatis")),
                    margin=str(params.get("margin", "Normal")),
                ),
                job.cancellation_token,
                progress,
            )
        elif job.tool_type == ToolType.MERGE_PDF:
            result = MergePdfService().merge(
                job.input_files,
                MergePdfOptions(job.options.output_dir, str(params.get("output_name", "gabungan.pdf"))),
                job.cancellation_token,
                progress,
            )
        elif job.tool_type == ToolType.SPLIT_PDF:
            result = SplitPdfService().split(
                job.input_files[0],
                SplitPdfOptions(job.options.output_dir, str(params.get("mode", "all_pages")), str(params.get("ranges", ""))),
                job.cancellation_token,
                progress,
            )
        elif job.tool_type == ToolType.COMPRESS_PDF:
            result = CompressPdfService().compress(
                job.input_files[0],
                CompressPdfOptions(job.options.output_dir, str(params.get("preset", "Seimbang")), bool(params.get("keep_if_larger", False))),
                job.cancellation_token,
                progress,
            )
        elif job.tool_type == ToolType.IMAGE_CONVERT:
            result = ImageConvertService().convert(
                job.input_files,
                ImageConvertOptions(job.options.output_dir, str(params.get("target_format", "JPEG")), int(params.get("quality", 90))),
                job.cancellation_token,
                progress,
            )
        elif job.tool_type == ToolType.IMAGE_RESIZE:
            result = ImageResizeService().resize(
                job.input_files,
                ImageResizeOptions(
                    output_dir=job.options.output_dir,
                    width=params.get("width"),  # type: ignore[arg-type]
                    height=params.get("height"),  # type: ignore[arg-type]
                    percent=params.get("percent"),  # type: ignore[arg-type]
                    keep_ratio=bool(params.get("keep_ratio", True)),
                    quality=int(params.get("quality", 90)),
                ),
                job.cancellation_token,
                progress,
            )
        elif job.tool_type == ToolType.IMAGE_COMPRESS:
            result = ImageCompressService().compress(
                job.input_files,
                ImageCompressOptions(job.options.output_dir, int(params.get("quality", 80))),
                job.cancellation_token,
                progress,
            )
        else:
            raise AppError("Fitur belum tersedia.")

        if job.options.create_zip and result.output_paths:
            zip_path = ZipService().create_zip(job.options.output_dir, result.output_paths)
            result.output_paths.append(zip_path)
        return result

    def _write_conversion_log(self, job: Job) -> None:
        try:
            job.options.output_dir.mkdir(parents=True, exist_ok=True)
            log_path = job.options.output_dir / "conversion_log.txt"
            lines = [
                "UBAHIN conversion log",
                f"Job ID: {job.job_id}",
                f"Tool: {job.tool_type.value}",
                f"Status: {job.status.value}",
                f"Mulai: {job.start_time.isoformat() if job.start_time else '-'}",
                f"Selesai: {job.end_time.isoformat() if job.end_time else '-'}",
                f"Durasi: {job.duration:.2f} detik" if job.duration is not None else "Durasi: -",
                f"Input: {len(job.input_files)} file",
                f"Output: {len(job.result.output_paths) if job.result else 0} file",
            ]
            if job.errors:
                lines.append("Error:")
                lines.extend(f"- {error}" for error in job.errors)
            if job.result and job.result.output_paths:
                lines.append("File hasil:")
                lines.extend(f"- {path}" for path in job.result.output_paths)
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            self.logger.exception("Gagal menulis conversion_log.txt")
