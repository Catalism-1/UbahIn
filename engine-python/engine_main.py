from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
import threading
import traceback
import uuid
from pathlib import Path
from typing import Any


ENGINE_VERSION = "0.1.2"


# ---------- engine logger ---------------------------------------------------

_engine_file_handler: logging.FileHandler | None = None
_engine_logger: logging.Logger | None = None


def _setup_engine_logger() -> logging.Logger:
    global _engine_file_handler, _engine_logger
    if _engine_logger is not None:
        return _engine_logger
    appdata = Path(os.environ.get("LOCALAPPDATA", "") or ".") / "Ubahin" / "logs"
    appdata.mkdir(parents=True, exist_ok=True)
    log_path = appdata / "engine.log"
    handler = logging.FileHandler(log_path, encoding="utf-8", delay=False)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("ubahin.engine_main")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    _engine_file_handler = handler
    _engine_logger = logger
    return logger


def _elog(message: str) -> None:
    """Write structured log to engine.log."""
    try:
        _setup_engine_logger().info(message)
    except Exception:
        pass


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
from ubahin.services import HistoryService, SettingsService
from ubahin.services.settings_service import AppSettings
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
            "inspect_image_files",
            "start_pdf_to_jpg",
            "start_image_to_pdf",
            "cancel_job",
            "get_job_status",
            "get_settings",
            "save_settings",
            "list_history",
            "get_recent_history",
            "delete_history_item",
            "clear_history",
            "open_history_output_directory",
            "shutdown",
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


def _inspect_image(path: Path) -> dict[str, Any]:
    import base64
    from io import BytesIO
    resolved = path.expanduser().resolve()
    file_id = str(uuid.uuid4())
    filename = resolved.name
    size_bytes = resolved.stat().st_size if resolved.exists() else 0
    base: dict[str, Any] = {
        "path": str(resolved),
        "file_id": file_id,
        "filename": filename,
        "size_bytes": size_bytes,
        "format": None,
        "width": 0,
        "height": 0,
        "status": "ready",
        "warning": None,
        "error": None,
        "thumbnail_data_uri": None,
    }
    try:
        if not resolved.exists():
            raise AppError("File tidak ditemukan.")
        if resolved.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise AppError("Format gambar tidak didukung.")
        
        from PIL import Image
        with Image.open(resolved) as img:
            base["format"] = img.format
            base["width"] = img.width
            base["height"] = img.height
            
            # Generate thumbnail: max 160px on longest side
            thumb_w = img.width
            thumb_h = img.height
            if thumb_w > 160 or thumb_h > 160:
                if thumb_w > thumb_h:
                    thumb_h = int(round(160 * (thumb_h / thumb_w)))
                    thumb_w = 160
                else:
                    thumb_w = int(round(160 * (thumb_w / thumb_h)))
                    thumb_h = 160
                    
            thumb_w = max(thumb_w, 1)
            thumb_h = max(thumb_h, 1)
            
            thumb = img.copy()
            thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            
            thumb_rgb = thumb
            if thumb.mode in ("RGBA", "LA") or (thumb.mode == "P" and "transparency" in thumb.info):
                thumb_rgb = Image.new("RGB", thumb.size, "white")
                thumb_rgb.paste(thumb, mask=thumb.convert("RGBA").split()[3])
            elif thumb.mode != "RGB":
                thumb_rgb = thumb.convert("RGB")
                
            buffered = BytesIO()
            thumb_rgb.save(buffered, format="JPEG", quality=75)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            base["thumbnail_data_uri"] = f"data:image/jpeg;base64,{img_str}"
            
            if thumb_rgb is not thumb:
                thumb_rgb.close()
            thumb.close()
    except Exception as exc:
        base["status"] = "failed"
        base["error"] = str(exc)
    return base


class EngineRuntime:
    def __init__(self) -> None:
        self._write_lock = threading.RLock()
        self._history = HistoryService()
        self._manager = JobManager(history_service=self._history)
        self._settings = SettingsService()
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
        if action == "inspect_image_files":
            return self._inspect_image_files(request_id, body)
        if action == "start_pdf_to_jpg":
            return self._start_pdf_to_jpg(request_id, body)
        if action == "start_image_to_pdf":
            return self._start_image_to_pdf(request_id, body)
        if action == "cancel_job":
            return self._cancel_job(request_id, body)
        if action == "get_job_status":
            return self._get_job_status(request_id, body)
        if action == "get_settings":
            return self._get_settings(request_id)
        if action == "save_settings":
            return self._save_settings(request_id, body)
        if action == "list_history":
            return self._list_history(request_id, body)
        if action == "get_recent_history":
            return self._get_recent_history(request_id, body)
        if action == "delete_history_item":
            return self._delete_history_item(request_id, body)
        if action == "clear_history":
            return self._clear_history(request_id, body)
        if action == "open_history_output_directory":
            return self._open_history_output_directory(request_id, body)
        if action == "shutdown":
            return self._shutdown(request_id, body)
        return _error(request_id, "Aksi engine tidak dikenal.", "UNKNOWN_ACTION")

    def _inspect_pdf_files(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        paths = payload.get("paths")
        if not isinstance(paths, list):
            return _error(request_id, "Payload paths harus berupa daftar file.", "INVALID_PAYLOAD")
        results = [_inspect_pdf(Path(str(path))) for path in paths[:50]]
        return _ok(request_id, {"files": results})

    def _inspect_image_files(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        paths = payload.get("paths")
        if not isinstance(paths, list):
            return _error(request_id, "Payload paths harus berupa daftar file.", "INVALID_PAYLOAD")
        results = [_inspect_image(Path(str(path))) for path in paths[:50]]
        return _ok(request_id, {"files": results})

    def _start_image_to_pdf(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = str(payload.get("job_id") or uuid.uuid4())
        raw_files = payload.get("files")
        if not isinstance(raw_files, list) or not raw_files:
            return _error(request_id, "Pilih minimal satu file gambar.", "INVALID_PAYLOAD")
        if len(raw_files) > 50:
            return _error(request_id, "Maksimal 50 gambar dalam satu antrean.", "TOO_MANY_FILES")

        output_directory = str(payload.get("output_directory") or "").strip()
        if not output_directory:
            return _error(request_id, "Pilih folder hasil terlebih dahulu.", "MISSING_OUTPUT_DIRECTORY")

        paths: list[Path] = []
        file_ids: dict[str, str] = {}
        for item in raw_files:
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("path") or ""))
            if not str(path):
                continue
            paths.append(path)
            file_ids[path.expanduser().resolve().name] = str(item.get("file_id") or "")

        if not paths:
            return _error(request_id, "Tidak ada file gambar valid untuk diproses.", "NO_INPUT_FILES")

        open_after_finish = bool(payload.get("open_output_after_finish", False))
        image_quality_preset = str(payload.get("image_quality_preset") or "balanced")
        jpeg_quality = int(payload.get("jpeg_quality") or 85)
        optimize_pdf_size = bool(payload.get("optimize_pdf_size", True))
        output_filename = str(payload.get("output_filename") or "hasil_gambar.pdf")

        _elog(
            f"IMAGE_TO_PDF_START job_id={job_id} files={len(paths)} "
            f"output_dir={output_directory!r} output_filename={output_filename!r}"
        )

        try:
            job = self._manager.create_job(
                ToolType.IMAGE_TO_PDF,
                paths,
                output_directory,
                job_id=job_id,
                output_name=output_filename,
                page_size=str(payload.get("page_size") or "original"),
                orientation=str(payload.get("orientation") or "auto"),
                margin=str(payload.get("margin") or "normal"),
                fit_mode=str(payload.get("fit_mode") or "contain"),
                image_quality_preset=image_quality_preset,
                jpeg_quality=jpeg_quality,
                optimize_pdf_size=optimize_pdf_size,
                performance_mode=_performance_mode(payload.get("performance_mode")),
            )
            self._job_meta[job.job_id] = {
                "total_pages": len(paths),
                "open_after_finish": open_after_finish,
                "file_ids": file_ids,
                "image_quality_preset": image_quality_preset,
                "jpeg_quality": jpeg_quality,
            }
            self._manager.start_job(job.job_id)
            _elog(f"IMAGE_TO_PDF_JOB_STARTED job_id={job.job_id} status={job.status.value}")
        except AppError as exc:
            _elog(f"IMAGE_TO_PDF_START_FAILED job_id={job_id} error={exc}")
            return _error(request_id, str(exc), "JOB_START_FAILED")
        except Exception as exc:
            _elog(f"IMAGE_TO_PDF_START_FAILED job_id={job_id} error={exc}")
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return _error(request_id, f"Tidak dapat memulai konversi: {exc}", "JOB_START_FAILED")

        return _ok(request_id, {"job_id": job.job_id, "status": job.status.value})

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

    # ---------------------------------------------------------------- settings
    def _get_settings(self, request_id: str | None) -> dict[str, Any]:
        try:
            settings = self._settings.load()
            return _ok(request_id, settings.to_protocol_dict())
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            # Default aman bila pembacaan gagal total.
            return _ok(request_id, AppSettings().to_protocol_dict())

    def _save_settings(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            settings = AppSettings.from_protocol_payload(payload)
            self._settings.save(settings)
            return _ok(request_id, settings.to_protocol_dict())
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return _error(request_id, "Pengaturan tidak dapat disimpan.", "SETTINGS_SAVE_FAILED")

    # ----------------------------------------------------------------- history
    def _list_history(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self._history.list_history(
                limit=int(payload.get("limit") or 50),
                offset=int(payload.get("offset") or 0),
                status=str(payload.get("status") or "all"),
                tool_type=str(payload.get("tool_type") or "all"),
            )
            return _ok(request_id, result)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return _error(request_id, "Riwayat tidak dapat dimuat.", "HISTORY_LIST_FAILED")

    def _get_recent_history(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            items = self._history.get_recent(limit=int(payload.get("limit") or 5))
            return _ok(request_id, {"items": items})
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return _error(request_id, "Riwayat terbaru tidak dapat dimuat.", "HISTORY_RECENT_FAILED")

    def _delete_history_item(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        history_id = str(payload.get("history_id") or "").strip()
        if not history_id:
            return _error(request_id, "ID riwayat tidak valid.", "INVALID_PAYLOAD")
        try:
            # Menghapus record TIDAK menghapus file hasil pengguna.
            deleted = self._history.delete(history_id)
            return _ok(request_id, {"deleted": deleted, "history_id": history_id})
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return _error(request_id, "Riwayat tidak dapat dihapus.", "HISTORY_DELETE_FAILED")

    def _clear_history(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            removed = self._history.clear()
            return _ok(request_id, {"removed": removed})
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return _error(request_id, "Riwayat tidak dapat dibersihkan.", "HISTORY_CLEAR_FAILED")

    def _open_history_output_directory(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        history_id = str(payload.get("history_id") or "").strip()
        if not history_id:
            return _error(request_id, "ID riwayat tidak valid.", "INVALID_PAYLOAD")
        output_dir = self._history.get_output_dir(history_id)
        if not output_dir:
            return _error(request_id, "Riwayat tidak ditemukan.", "HISTORY_NOT_FOUND")
        path = Path(output_dir)
        if not path.exists():
            return _error(request_id, "Folder hasil tidak ditemukan.", "OUTPUT_DIR_MISSING")
        return _ok(request_id, {"path": str(path), "exists": True})

    def _shutdown(self, request_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        cancel_active = bool(payload.get("cancel_active", True))
        try:
            timeout_seconds = float(payload.get("timeout_seconds") or 2.0)
        except (TypeError, ValueError):
            timeout_seconds = 2.0
        timeout_seconds = max(0.0, min(timeout_seconds, 10.0))

        active_before = [job.job_id for job in self._manager.get_active_jobs()]
        cleanup_completed = True
        if cancel_active:
            cleanup_completed = self._manager.shutdown_gracefully(timeout=timeout_seconds)
        active_remaining = [job.job_id for job in self._manager.get_active_jobs()]

        return _ok(
            request_id,
            {
                "message": "Engine ditutup dengan aman",
                "cancel_active": cancel_active,
                "cleanup_completed": cleanup_completed,
                "active_jobs_before": active_before,
                "active_jobs_remaining": active_remaining,
                "sqlite_connections": "closed_per_operation",
            },
        )

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
            # Only include output paths that actually exist on disk and are non-empty
            output_paths = [
                path for path in (result.output_paths if result else [])
                if path.exists() and path.stat().st_size > 0
            ]
            jpg_outputs = [path for path in output_paths if path.suffix.lower() in {".jpg", ".jpeg"}]
            pdf_outputs = [path for path in output_paths if path.suffix.lower() == ".pdf"]
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
            meta = self._job_meta.get(job.job_id, {})
            tool_type = job.tool_type.value if hasattr(job.tool_type, "value") else str(job.tool_type)

            # For IMAGE_TO_PDF: provide explicit output_pdf_path and output_filename
            output_pdf_path = ""
            output_filename = ""
            output_size_bytes = sum(p.stat().st_size for p in output_paths if p.exists())
            if pdf_outputs:
                output_pdf_path = _json_safe_path(pdf_outputs[0])
                output_filename = pdf_outputs[0].name
                output_size_bytes = pdf_outputs[0].stat().st_size

            return {
                "job_id": job.job_id,
                "tool_type": tool_type,
                "status": job.status.value,
                "successful_files": result.successful_files if result else 0,
                "failed_files": result.failed_files if result else len(job.input_files),
                "skipped_files": result.skipped_files if result else 0,
                "total_input_files": result.total_input_files if result else len(job.input_files),
                "processed_files": result.processed_files if result else 0,
                "total_outputs": len(output_paths),
                "total_jpg": len(jpg_outputs),
                "output_size_bytes": output_size_bytes,
                "output_pdf_path": output_pdf_path,
                "output_filename": output_filename,
                "output_directory": str(job.options.output_dir),
                "output_paths": [_json_safe_path(path) for path in output_paths],
                "duration_seconds": job.duration,
                "warnings": list(job.warnings),
                "errors": list(job.errors),
                "failed_file_details": failed_files,
                "image_quality_preset": meta.get("image_quality_preset", ""),
                "jpeg_quality": meta.get("jpeg_quality", 0),
            }

        def on_completed(job: Job) -> None:
            tool_type = job.tool_type.value if hasattr(job.tool_type, "value") else str(job.tool_type)
            _elog(f"ENGINE_JOB_COMPLETED_HANDLER job_id={job.job_id} tool_type={tool_type}")

            emit_file_events(job)
            payload = result_payload(job)

            # Safety gate for IMAGE_TO_PDF: if no valid PDF output, escalate to job_failed
            if tool_type == "image_to_pdf":
                output_pdf_path = payload.get("output_pdf_path", "")
                output_size = payload.get("output_size_bytes", 0)
                if not output_pdf_path or not output_size:
                    error_msg = "PDF belum berhasil dibuat. Silakan buka log untuk melihat detail."
                    _elog(
                        f"ENGINE_EVENT_SENT job_failed (safety gate) job_id={job.job_id} "
                        f"output_pdf_path={output_pdf_path!r} output_size={output_size}"
                    )
                    # Inject error and emit job_failed
                    payload["status"] = "failed"
                    payload["errors"] = [error_msg] + list(payload.get("errors") or [])
                    self.write_message(_event("job_failed", job.job_id, payload))
                    return

                _elog(
                    f"ENGINE_EVENT_SENT job_completed job_id={job.job_id} "
                    f"output_pdf_path={output_pdf_path!r} size={output_size}"
                )
            else:
                _elog(f"ENGINE_EVENT_SENT job_completed job_id={job.job_id} tool_type={tool_type}")

            self.write_message(_event("job_completed", job.job_id, payload))

            meta = self._job_meta.get(job.job_id, {})
            if meta.get("open_after_finish"):
                try:
                    open_in_file_manager(job.options.output_dir)
                except Exception:
                    print(traceback.format_exc(), file=sys.stderr, flush=True)

        def on_failed(job: Job) -> None:
            tool_type = job.tool_type.value if hasattr(job.tool_type, "value") else str(job.tool_type)
            _elog(f"ENGINE_EVENT_SENT job_failed job_id={job.job_id} tool_type={tool_type}")
            emit_file_events(job)
            self.write_message(_event("job_failed", job.job_id, result_payload(job)))

        def on_cancelled(job: Job) -> None:
            tool_type = job.tool_type.value if hasattr(job.tool_type, "value") else str(job.tool_type)
            _elog(f"ENGINE_EVENT_SENT job_cancelled job_id={job.job_id} tool_type={tool_type}")
            emit_file_events(job)
            self.write_message(_event("job_cancelled", job.job_id, result_payload(job)))

        self._manager.add_callback("on_job_started", on_started)
        self._manager.add_callback("on_progress", on_progress)
        self._manager.add_callback("on_job_completed", on_completed)
        self._manager.add_callback("on_job_failed", on_failed)
        self._manager.add_callback("on_job_cancelled", on_cancelled)


def run_stdio() -> int:
    appdata = Path(os.environ.get("LOCALAPPDATA", "") or ".") / "Ubahin" / "logs"
    appdata.mkdir(parents=True, exist_ok=True)
    try:
        sys.stderr = open(appdata / "engine.stderr.log", "a", encoding="utf-8")
    except Exception:
        pass
    # Initialize engine logger now that stderr is redirected
    _setup_engine_logger()
    _elog("ENGINE_STDIO_STARTED")

    runtime = EngineRuntime()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        payload: object | None = None
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("Request harus berupa object JSON.")
            response = runtime.handle_request(payload)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            response = _error(None, "Engine tidak dapat memproses request.")
        runtime.write_message(response)

        # Jika menerima instruksi shutdown, keluar dengan aman
        if isinstance(payload, dict) and payload.get("action") == "shutdown":
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:
                pass
            logging.shutdown()
            return 0
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
