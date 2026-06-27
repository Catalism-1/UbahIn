from __future__ import annotations

import argparse
import json
import platform
import sys
import threading
import traceback
import uuid
from pathlib import Path
from typing import Any


ENGINE_VERSION = "0.1.1"


def _add_legacy_src_to_path() -> None:
    root = Path(__file__).resolve().parents[1]
    if root.name == "engine-python":
        root = root.parent
    legacy_src = root / "src"
    if legacy_src.exists():
        sys.path.insert(0, str(legacy_src))


_add_legacy_src_to_path()

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - reported by health check
    fitz = None  # type: ignore

from ubahin.core import JobManager, ToolType
from ubahin.core.job import Job
from ubahin.core.models import AppError
from ubahin.core.progress import ProgressInfo
from ubahin.services import HistoryService
from ubahin.utils import open_in_file_manager


def _module_available(name: str) -> bool:
    try:
        __import__(name)
    except Exception:
        return False
    return True


def _platform_name() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return system or sys.platform


def _native_acceleration() -> str:
    try:
        from ubahin.native_bridge import native_status

        status = native_status()
        if status.get("available"):
            return str(status.get("backend") or "native")
    except Exception:
        pass
    return "fallback"


def _health_data() -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "python_available": True,
        "pymupdf_available": _module_available("fitz"),
        "pillow_available": _module_available("PIL"),
        "pypdf_available": _module_available("pypdf"),
        "native_acceleration": _native_acceleration(),
        "platform": _platform_name(),
    }


def _app_info() -> dict[str, Any]:
    return {
        "name": "Ubahin Engine",
        "engine_version": ENGINE_VERSION,
        "protocol": "json-lines",
        "platform": _platform_name(),
        "actions": [
            "health",
            "app_info",
            "self_check",
            "inspect_pdf_files",
            "start_pdf_to_jpg",
            "cancel_job",
            "get_job_status",
        ],
    }


def _self_check() -> dict[str, Any]:
    checks = _health_data()
    checks["ok"] = bool(checks["pymupdf_available"] and checks["pillow_available"] and checks["pypdf_available"])
    return checks


def _ok(request_id: str | None, data: dict[str, Any]) -> dict[str, Any]:
    return {"type": "response", "id": request_id, "ok": True, "data": data}


def _error(request_id: str | None, message: str, code: str = "ENGINE_ERROR") -> dict[str, Any]:
    return {
        "type": "response",
        "id": request_id,
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _event(name: str, job_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"type": "event", "event": name, "job_id": job_id, "data": data}


def _json_safe_path(path: Path) -> str:
    return str(path)


def _performance_mode(value: object) -> str:
    raw = str(value or "balanced").lower()
    return {
        "ram_saver": "hemat_ram",
        "hemat_ram": "hemat_ram",
        "balanced": "seimbang",
        "seimbang": "seimbang",
        "fast": "cepat",
        "cepat": "cepat",
    }.get(raw, "seimbang")


def _inspect_pdf(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    file_id = str(uuid.uuid4())
    filename = resolved.name
    size_bytes = resolved.stat().st_size if resolved.exists() else 0
    base: dict[str, Any] = {
        "path": str(resolved),
        "file_id": file_id,
        "filename": filename,
        "size_bytes": size_bytes,
        "page_count": 0,
        "status": "ready",
        "warning": None,
        "error": None,
    }
    try:
        if not resolved.exists():
            raise AppError("File tidak ditemukan.")
        if resolved.suffix.lower() != ".pdf":
            raise AppError("File bukan PDF.")
        if fitz is None:
            raise AppError("PyMuPDF tidak tersedia.")
        with fitz.open(resolved) as document:
            if document.needs_pass:
                raise AppError("PDF terkunci password.")
            if document.page_count <= 0:
                raise AppError("PDF tidak memiliki halaman.")
            base["page_count"] = document.page_count
    except Exception as exc:
        base["status"] = "failed"
        base["error"] = str(exc)
    return base


class EngineRuntime:
    def __init__(self) -> None:
        self._write_lock = threading.RLock()
        self._manager = JobManager(history_service=HistoryService())
        self._job_meta: dict[str, dict[str, Any]] = {}
        self._wire_events()

    def write_message(self, message: dict[str, Any]) -> None:
        with self._write_lock:
            print(json.dumps(message, ensure_ascii=False, default=str), flush=True)

    def handle_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("id")
        action = payload.get("action")
        body = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}

        if action == "health":
            return _ok(request_id, _health_data())
        if action == "app_info":
            return _ok(request_id, _app_info())
        if action == "self_check":
            data = _self_check()
            if data["ok"]:
                return _ok(request_id, data)
            return _error(request_id, "Komponen engine belum lengkap.")
        if action == "inspect_pdf_files":
            return self._inspect_pdf_files(request_id, body)
        if action == "start_pdf_to_jpg":
            return self._start_pdf_to_jpg(request_id, body)
        if action == "cancel_job":
            return self._cancel_job(request_id, body)
        if action == "get_job_status":
            return self._get_job_status(request_id, body)
        return _error(request_id, "Aksi engine tidak dikenal.", "UNKNOWN_ACTION")

    def _inspect_pdf_files(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        paths = payload.get("paths")
        if not isinstance(paths, list):
            return _error(request_id, "Payload paths harus berupa daftar file.", "INVALID_PAYLOAD")
        results = [_inspect_pdf(Path(str(path))) for path in paths[:50]]
        return _ok(request_id, {"files": results})

    def _start_pdf_to_jpg(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = str(payload.get("job_id") or uuid.uuid4())
        raw_files = payload.get("files")
        if not isinstance(raw_files, list) or not raw_files:
            return _error(request_id, "Pilih minimal satu file PDF.", "INVALID_PAYLOAD")
        if len(raw_files) > 50:
            return _error(request_id, "Maksimal 50 file PDF dalam satu antrean.", "TOO_MANY_FILES")

        output_directory = str(payload.get("output_directory") or "").strip()
        if not output_directory:
            return _error(request_id, "Pilih folder hasil terlebih dahulu.", "MISSING_OUTPUT_DIRECTORY")

        paths: list[Path] = []
        file_ids: dict[str, str] = {}
        total_pages = 0
        for item in raw_files:
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("path") or ""))
            if not str(path):
                continue
            paths.append(path)
            file_ids[path.expanduser().resolve().name] = str(item.get("file_id") or "")
            try:
                inspected = _inspect_pdf(path)
                total_pages += int(inspected.get("page_count") or 0)
            except Exception:
                pass
        if not paths:
            return _error(request_id, "Tidak ada file PDF valid untuk diproses.", "NO_INPUT_FILES")

        create_zip = bool(payload.get("create_zip", False))
        open_after_finish = bool(payload.get("open_output_after_finish", False))
        optimize_size = bool(payload.get("optimize_file_size", True))

        try:
            job = self._manager.create_job(
                ToolType.PDF_TO_JPG,
                paths,
                output_directory,
                job_id=job_id,
                preset=str(payload.get("preset") or "standard"),
                dpi=int(payload.get("dpi") or 150),
                jpg_quality=int(payload.get("jpeg_quality") or 80),
                optimize_size=optimize_size,
                create_zip=create_zip,
                performance_mode=_performance_mode(payload.get("performance_mode")),
            )
            self._job_meta[job.job_id] = {
                "total_pages": total_pages,
                "open_after_finish": open_after_finish,
                "file_ids": file_ids,
            }
            self._manager.start_job(job.job_id)
        except AppError as exc:
            return _error(request_id, str(exc), "JOB_START_FAILED")
        except Exception as exc:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return _error(request_id, f"Tidak dapat memulai konversi: {exc}", "JOB_START_FAILED")

        return _ok(request_id, {"job_id": job.job_id, "status": job.status.value})

    def _cancel_job(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = str(payload.get("job_id") or "")
        if not job_id:
            return _error(request_id, "Job ID tidak valid.", "INVALID_PAYLOAD")
        try:
            self._manager.cancel_job(job_id)
            return _ok(request_id, {"job_id": job_id, "status": "cancelling"})
        except KeyError:
            return _error(request_id, "Job tidak ditemukan.", "JOB_NOT_FOUND")
        except Exception as exc:
            return _error(request_id, f"Tidak dapat membatalkan job: {exc}", "CANCEL_FAILED")

    def _get_job_status(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = str(payload.get("job_id") or "")
        if not job_id:
            return _error(request_id, "Job ID tidak valid.", "INVALID_PAYLOAD")
        try:
            job = self._manager.get_job(job_id)
            return _ok(request_id, {"job": job.to_dict()})
        except KeyError:
            return _error(request_id, "Job tidak ditemukan.", "JOB_NOT_FOUND")

    def _wire_events(self) -> None:
        def on_started(job: Job) -> None:
            self.write_message(
                _event(
                    "job_started",
                    job.job_id,
                    {
                        "job_id": job.job_id,
                        "total_files": len(job.input_files),
                        "total_pages": self._job_meta.get(job.job_id, {}).get("total_pages", 0),
                    },
                )
            )

        def on_progress(job: Job, progress: ProgressInfo) -> None:
            file_percent = 0
            if progress.total_pages > 0:
                file_percent = int(round(progress.current_page / progress.total_pages * 100))
            self.write_message(
                _event(
                    "progress",
                    job.job_id,
                    {
                        "current_file": progress.current_file,
                        "current_file_index": progress.current_item,
                        "total_files": progress.total_items,
                        "current_page": progress.current_page,
                        "total_pages": progress.total_pages,
                        "overall_percent": round(progress.percentage, 1),
                        "file_percent": file_percent,
                        "message": progress.message
                        or f"Mengubah halaman {progress.current_page} dari {progress.total_pages}",
                    },
                )
            )

        def emit_file_events(job: Job) -> None:
            if not job.result:
                return
            meta = self._job_meta.get(job.job_id, {})
            file_ids = meta.get("file_ids", {})
            if not isinstance(file_ids, dict):
                file_ids = {}
            for file_result in job.result.file_results:
                filename = file_result.input_path.name
                payload = {
                    "file_id": file_ids.get(filename, ""),
                    "filename": filename,
                    "path": str(file_result.input_path),
                    "status": file_result.status,
                    "output_count": len(file_result.output_paths),
                    "output_paths": [_json_safe_path(path) for path in file_result.output_paths],
                    "error": file_result.error,
                }
                if file_result.status == "completed":
                    self.write_message(_event("file_completed", job.job_id, payload))
                elif file_result.status == "failed":
                    self.write_message(
                        _event(
                            "warning",
                            job.job_id,
                            {
                                **payload,
                                "message": f"{filename}: {file_result.error or 'Tidak dapat diproses'}",
                            },
                        )
                    )

        def result_payload(job: Job) -> dict[str, Any]:
            result = job.result
            output_paths = list(result.output_paths) if result else []
            jpg_outputs = [path for path in output_paths if path.suffix.lower() in {".jpg", ".jpeg"}]
            failed_files = []
            if result:
                failed_files = [
                    {
                        "filename": item.input_path.name,
                        "path": str(item.input_path),
                        "error": item.error or "Tidak dapat diproses",
                    }
                    for item in result.file_results
                    if item.status == "failed"
                ]
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "successful_files": result.successful_files if result else 0,
                "failed_files": result.failed_files if result else len(job.input_files),
                "skipped_files": result.skipped_files if result else 0,
                "total_input_files": result.total_input_files if result else len(job.input_files),
                "processed_files": result.processed_files if result else 0,
                "total_outputs": len(output_paths),
                "total_jpg": len(jpg_outputs),
                "output_directory": str(job.options.output_dir),
                "output_paths": [_json_safe_path(path) for path in output_paths],
                "duration_seconds": job.duration,
                "warnings": list(job.warnings),
                "errors": list(job.errors),
                "failed_file_details": failed_files,
            }

        def on_completed(job: Job) -> None:
            emit_file_events(job)
            self.write_message(_event("job_completed", job.job_id, result_payload(job)))
            meta = self._job_meta.get(job.job_id, {})
            if meta.get("open_after_finish"):
                try:
                    open_in_file_manager(job.options.output_dir)
                except Exception:
                    print(traceback.format_exc(), file=sys.stderr, flush=True)

        def on_failed(job: Job) -> None:
            emit_file_events(job)
            self.write_message(_event("job_failed", job.job_id, result_payload(job)))

        def on_cancelled(job: Job) -> None:
            emit_file_events(job)
            self.write_message(_event("job_cancelled", job.job_id, result_payload(job)))

        self._manager.add_callback("on_job_started", on_started)
        self._manager.add_callback("on_progress", on_progress)
        self._manager.add_callback("on_job_completed", on_completed)
        self._manager.add_callback("on_job_failed", on_failed)
        self._manager.add_callback("on_job_cancelled", on_cancelled)


def run_stdio() -> int:
    runtime = EngineRuntime()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("Request harus berupa object JSON.")
            response = runtime.handle_request(payload)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            response = _error(None, "Engine tidak dapat memproses request.")
        runtime.write_message(response)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ubahin-engine")
    parser.add_argument("--stdio", action="store_true", help="Run JSON Lines protocol on stdin/stdout.")
    args = parser.parse_args(argv)
    if args.stdio:
        return run_stdio()
    print("Gunakan --stdio untuk menjalankan Ubahin Engine sebagai sidecar.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
