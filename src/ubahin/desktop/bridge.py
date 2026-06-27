"""Python ↔ JavaScript bridge for the pywebview desktop frontend.

All methods on :class:`DesktopBridge` are exposed to JavaScript via
``window.pywebview.api``.  Every response returns the same envelope shape so
the frontend can treat results uniformly::

    {"success": bool, "message": str, "data": dict}

Job events emitted by the modern :class:`ubahin.core.JobManager` are
forwarded to the WebView on the GUI thread through ``evaluate_js``.
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from ubahin.core import JobManager, ToolType
from ubahin.core.job import Job
from ubahin.core.models import AppError
from ubahin.core.progress import ProgressInfo
from ubahin.desktop.self_check import run_self_check
from ubahin.native_bridge import native_status
from ubahin.services import HistoryService, SettingsService
from ubahin.utils import get_app_data_dir, get_log_dir, get_logger, open_in_file_manager

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - PyMuPDF should always be available
    fitz = None  # type: ignore


VERSION = "0.1.1"
LOGGER = logging.getLogger("ubahin.bridge")


def _ok(message: str = "", data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": True, "message": message, "data": data or {}}


def _err(message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": False, "message": message, "data": data or {}}


class DesktopBridge:
    """API exposed to JavaScript."""

    def __init__(self) -> None:
        self.job_manager = JobManager()
        self.history_service: HistoryService = self.job_manager.history_service
        self.settings_service = SettingsService()
        self.logger = get_logger("ubahin.bridge")
        self.frontend_logger = self._build_frontend_logger()
        self._window = None  # set after pywebview window is created
        self._selected_files: dict[str, dict[str, Any]] = {}
        self._last_output_folder: Path | None = None
        self._jobs_meta: dict[str, dict[str, Any]] = {}
        self._is_maximized = False
        self._lock = threading.RLock()
        self._wire_job_events()

    def _build_frontend_logger(self) -> logging.Logger:
        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("ubahin.frontend")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        log_path = log_dir / "frontend.log"
        if not any(
            isinstance(handler, RotatingFileHandler)
            and Path(getattr(handler, "baseFilename", "")) == log_path
            for handler in logger.handlers
        ):
            handler = RotatingFileHandler(
                log_path,
                maxBytes=1_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            logger.addHandler(handler)
        return logger

    # --------- pywebview hooks ---------
    def attach_window(self, window: Any) -> None:
        self._window = window

    def detach_window(self) -> None:
        self._window = None

    # --------- event dispatch ---------
    def _dispatch(self, name: str, payload: dict[str, Any]) -> None:
        if self._window is None:
            return
        try:
            data = json.dumps(payload, ensure_ascii=False)
            script = f"window.__ubahinDispatch && window.__ubahinDispatch({json.dumps(name)}, {data});"
            self._window.evaluate_js(script)
        except Exception:
            self.logger.exception("Gagal mengirim event ke UI: %s", name)

    def _wire_job_events(self) -> None:
        def on_started(job: Job) -> None:
            meta = self._jobs_meta.get(job.job_id, {})
            self._dispatch(
                "job_started",
                {
                    "job_id": job.job_id,
                    "total_files": len(job.input_files),
                    "total_pages": meta.get("total_pages", 0),
                },
            )

        def on_progress(job: Job, progress: ProgressInfo) -> None:
            meta = self._jobs_meta.get(job.job_id, {})
            file_pct = 0
            if progress.total_pages > 0:
                file_pct = int(round(progress.current_page / progress.total_pages * 100))
            self._dispatch(
                "progress",
                {
                    "job_id": job.job_id,
                    "overall_percent": round(progress.percentage, 1),
                    "file_percent": file_pct,
                    "current_file": progress.current_file,
                    "current_page": progress.current_page,
                    "total_pages": progress.total_pages,
                    "completed_files": meta.get("completed_files", 0),
                    "total_files": len(job.input_files),
                    "message": progress.message,
                },
            )

        def on_completed(job: Job) -> None:
            result = job.result
            outputs = list(result.output_paths) if result else []
            self._last_output_folder = job.options.output_dir
            warnings = list(job.warnings) if job.warnings else []
            failed_files = result.failed_files if result else 0
            successful_files = result.successful_files if result else len(job.input_files)
            jpg_outputs = [path for path in outputs if Path(path).suffix.lower() in {".jpg", ".jpeg"}]
            if result is not None:
                for fr in result.file_results:
                    payload = {
                        "filename": fr.input_path.name,
                        "output_count": len(fr.output_paths),
                    }
                    if fr.status == "failed":
                        payload["error"] = fr.error or "Tidak dapat diproses"
                        self._dispatch("file_failed", payload)
                    elif fr.status == "completed":
                        self._dispatch("file_completed", payload)
            self._dispatch(
                "job_completed",
                {
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "completed_files": successful_files,
                    "failed_files": failed_files,
                    "skipped_files": result.skipped_files if result else 0,
                    "total_input_files": result.total_input_files if result else len(job.input_files),
                    "processed_files": result.processed_files if result else len(job.input_files),
                    "total_outputs": len(outputs),
                    "total_images": len(jpg_outputs),
                    "output_folder": str(job.options.output_dir),
                    "duration_seconds": job.duration,
                    "warnings": warnings,
                },
            )

        def on_failed(job: Job) -> None:
            result = job.result
            if result is not None:
                for fr in result.file_results:
                    if fr.status == "failed":
                        self._dispatch(
                            "file_failed",
                            {
                                "filename": fr.input_path.name,
                                "output_count": len(fr.output_paths),
                                "error": fr.error or "Tidak dapat diproses",
                            },
                        )
            self._dispatch(
                "job_failed",
                {
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "message": "; ".join(job.errors[:3]) or "Konversi gagal.",
                    "failed_files": result.failed_files if result else len(job.input_files),
                    "total_input_files": result.total_input_files if result else len(job.input_files),
                },
            )

        def on_cancelled(job: Job) -> None:
            self._dispatch("job_cancelled", {"job_id": job.job_id})

        self.job_manager.add_callback("on_job_started", on_started)
        self.job_manager.add_callback("on_progress", on_progress)
        self.job_manager.add_callback("on_job_completed", on_completed)
        self.job_manager.add_callback("on_job_failed", on_failed)
        self.job_manager.add_callback("on_job_cancelled", on_cancelled)

    # ------------------------------------------------------------------
    # JS-callable API. All methods are wrapped to never raise.
    # ------------------------------------------------------------------
    def get_app_info(self) -> dict[str, Any]:
        try:
            import os

            app_dir = get_app_data_dir()
            log_dir = get_log_dir()
            native = native_status()
            return _ok(
                data={
                    "name": "Ubahin",
                    "version": VERSION,
                    "app_data_dir": str(app_dir),
                    "log_dir": str(log_dir),
                    "native": native,
                    "performance_mode": self.settings_service.load().performance_mode.value,
                    "debug": os.environ.get("UBAHIN_DEBUG_WEBVIEW") == "1",
                }
            )
        except Exception as exc:  # pragma: no cover
            self.logger.exception("get_app_info gagal")
            return _err(f"Tidak dapat membaca info aplikasi: {exc}")

    def log_frontend(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            data = payload if isinstance(payload, dict) else {"message": str(payload)}
            level = str(data.get("level") or "info").lower()
            message = json.dumps(data, ensure_ascii=False, default=str, sort_keys=True)
            if level == "error":
                self.frontend_logger.error(message)
            elif level == "warning":
                self.frontend_logger.warning(message)
            else:
                self.frontend_logger.info(message)
            return _ok()
        except Exception as exc:
            self.logger.exception("log_frontend gagal")
            return _err(f"Tidak dapat menulis log frontend: {exc}")

    def window_action(self, action: str) -> dict[str, Any]:
        if self._window is None:
            return _err("Jendela belum siap.")
        try:
            if action == "minimize":
                self._window.minimize()
            elif action == "maximize":
                if self._is_maximized and hasattr(self._window, "restore"):
                    self._window.restore()
                    self._is_maximized = False
                else:
                    self._window.maximize()
                    self._is_maximized = True
            elif action == "close":
                self._window.destroy()
            else:
                return _err(f"Aksi tidak dikenal: {action}")
            return _ok()
        except Exception as exc:
            return _err(f"Tidak dapat menjalankan aksi jendela: {exc}")

    def select_pdf_files(self) -> dict[str, Any]:
        if self._window is None:
            return _err("Jendela belum siap.")
        try:
            import webview

            file_types = ("Dokumen PDF (*.pdf)", "Semua file (*.*)")
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=True,
                file_types=file_types,
            )
            paths = list(result or [])
            files: list[dict[str, Any]] = []
            for raw in paths:
                path = Path(raw)
                meta = self._inspect(path)
                if meta is None:
                    continue
                self._selected_files[meta["id"]] = meta
                files.append(meta)
                if len(files) + (len(self._selected_files) - len(files)) >= 50:
                    break
            return _ok(data={"files": files})
        except Exception as exc:
            self.logger.exception("select_pdf_files gagal")
            return _err(f"Pemilih file gagal: {exc}")

    def _inspect(self, path: Path) -> dict[str, Any] | None:
        try:
            size = path.stat().st_size
            pages = 0
            if fitz is not None:
                try:
                    with fitz.open(path) as doc:
                        pages = doc.page_count
                except Exception:
                    pages = 0
            file_id = str(uuid.uuid4())
            return {
                "id": file_id,
                "name": path.name,
                "path": str(path),
                "size": size,
                "pages": pages,
                "status": "ready",
            }
        except OSError as exc:
            self.logger.warning("Tidak dapat membaca %s: %s", path, exc)
            return None

    def remove_selected_file(self, file_id: str) -> dict[str, Any]:
        self._selected_files.pop(file_id, None)
        return _ok()

    def clear_selected_files(self) -> dict[str, Any]:
        self._selected_files.clear()
        return _ok()

    def select_output_folder(self) -> dict[str, Any]:
        if self._window is None:
            return _err("Jendela belum siap.")
        try:
            import webview

            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            paths = list(result or [])
            if not paths:
                return _ok()
            folder = str(Path(paths[0]))
            settings = self.settings_service.load()
            settings.default_output_dir = folder
            self.settings_service.save(settings)
            return _ok(data={"folder": folder})
        except Exception as exc:
            self.logger.exception("select_output_folder gagal")
            return _err(f"Pemilih folder gagal: {exc}")

    def get_settings(self) -> dict[str, Any]:
        try:
            settings = self.settings_service.load()
            payload = settings.to_dict()
            if not payload.get("default_output_dir"):
                home = Path.home() / "Documents" / "Ubahin"
                home.mkdir(parents=True, exist_ok=True)
                payload["default_output_dir"] = str(home)
                settings.default_output_dir = str(home)
                self.settings_service.save(settings)
            return _ok(data=payload)
        except Exception as exc:
            self.logger.exception("get_settings gagal")
            return _err(f"Tidak dapat membaca pengaturan: {exc}")

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            current = self.settings_service.load()
            for key in (
                "theme",
                "default_output_dir",
                "performance_mode",
                "default_jpg_quality",
                "default_dpi",
                "notify_on_completion",
                "open_output_after_finish",
                "auto_zip_after_finish",
            ):
                if key in payload and payload[key] is not None:
                    if key == "performance_mode":
                        try:
                            from ubahin.core.models import PerformanceMode

                            current.performance_mode = PerformanceMode(payload[key])
                        except Exception:
                            pass
                    elif key in {"default_jpg_quality", "default_dpi"}:
                        try:
                            setattr(current, key, int(payload[key]))
                        except Exception:
                            pass
                    elif key in {"notify_on_completion", "open_output_after_finish", "auto_zip_after_finish"}:
                        setattr(current, key, bool(payload[key]))
                    else:
                        setattr(current, key, str(payload[key]))
            self.settings_service.save(current)
            return _ok(data=current.to_dict())
        except Exception as exc:
            self.logger.exception("save_settings gagal")
            return _err(f"Tidak dapat menyimpan pengaturan: {exc}")

    def start_pdf_to_jpg_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            file_ids = list(payload.get("files") or [])
            paths: list[Path] = []
            total_pages = 0
            for file_id in file_ids:
                meta = self._selected_files.get(file_id)
                if not meta:
                    continue
                paths.append(Path(meta["path"]))
                total_pages += int(meta.get("pages") or 0)
            if not paths:
                return _err("Pilih minimal satu file PDF.")
            if len(paths) > 50:
                return _err("Maksimal 50 file PDF dalam satu antrean.")

            output_folder = Path(payload.get("output_folder") or "").expanduser()
            if not str(output_folder):
                return _err("Pilih folder hasil terlebih dahulu.")

            preset = str(payload.get("preset") or "Tinggi")
            try:
                dpi = int(payload.get("dpi") or 200)
            except Exception:
                dpi = 200
            try:
                jpg_quality = int(payload.get("jpg_quality") or 90)
            except Exception:
                jpg_quality = 90
            create_zip = bool(payload.get("create_zip"))
            optimize_size = bool(payload.get("optimize_size", True))
            performance_mode = str(payload.get("performance_mode") or "seimbang")

            job = self.job_manager.create_job(
                ToolType.PDF_TO_JPG,
                paths,
                output_folder,
                preset=preset,
                dpi=dpi,
                jpg_quality=jpg_quality,
                optimize_size=optimize_size,
                create_zip=create_zip,
                performance_mode=performance_mode,
            )
            self._jobs_meta[job.job_id] = {
                "total_pages": total_pages,
                "completed_files": 0,
                "open_after_finish": bool(payload.get("open_after_finish")),
            }
            self.job_manager.start_job(job.job_id)
            return _ok(message="Konversi dimulai.", data={"job_id": job.job_id})
        except AppError as exc:
            return _err(str(exc))
        except Exception as exc:
            self.logger.exception("start_pdf_to_jpg_job gagal")
            return _err(f"Tidak dapat memulai konversi: {exc}")

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        try:
            self.job_manager.cancel_job(job_id)
            return _ok(message="Permintaan batal dikirim.")
        except KeyError:
            return _err("Job tidak ditemukan.")
        except Exception as exc:
            return _err(f"Tidak dapat membatalkan job: {exc}")

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        try:
            job = self.job_manager.get_job(job_id)
            return _ok(data=job.to_dict())
        except KeyError:
            return _err("Job tidak ditemukan.")

    def open_output_folder(self, path: str | None = None) -> dict[str, Any]:
        try:
            target = Path(path) if path else self._last_output_folder
            if target is None:
                return _err("Belum ada folder hasil yang dapat dibuka.")
            target = Path(target)
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
            open_in_file_manager(target)
            return _ok()
        except Exception as exc:
            return _err(f"Tidak dapat membuka folder: {exc}")

    def open_log_folder(self) -> dict[str, Any]:
        try:
            open_in_file_manager(get_log_dir())
            return _ok()
        except Exception as exc:
            return _err(f"Tidak dapat membuka folder log: {exc}")

    def get_recent_history(self, limit: int = 50) -> dict[str, Any]:
        try:
            limit_int = max(1, min(int(limit or 50), 200))
            items = self.history_service.list_recent(limit=limit_int)
            return _ok(data={"items": items})
        except Exception as exc:
            self.logger.exception("get_recent_history gagal")
            return _err(f"Tidak dapat membaca riwayat: {exc}", data={"items": []})

    def get_system_check(self) -> dict[str, Any]:
        try:
            report = run_self_check()
            app_dir = Path(report.app_data_dir)
            disk = shutil.disk_usage(app_dir if app_dir.exists() else Path.cwd())
            disk_ok = disk.free > 500 * 1024 * 1024  # 500MB minimum
            data: dict[str, Any] = {
                "ok": report.ok,
                "generated_at": report.generated_at,
                "app_data_dir": report.app_data_dir,
                "log_dir": report.log_dir,
                "disk_free": disk.free,
                "disk_total": disk.total,
                "disk_ok": disk_ok,
                "native": report.native,
                "checks": [
                    {"name": c.name, "ok": c.ok, "message": c.message} for c in report.checks
                ],
            }
            return _ok(data=data)
        except Exception as exc:
            self.logger.exception("get_system_check gagal")
            return _err(f"Tidak dapat menjalankan pemeriksaan sistem: {exc}")
