from __future__ import annotations

from pathlib import Path
from typing import Any

from ubahin.core import JobManager, ToolType
from ubahin.core.models import AppError
from ubahin.ui_bridge.view_models import job_to_view_model


class AppController:
    def __init__(self, job_manager: JobManager | None = None) -> None:
        self.job_manager = job_manager or JobManager()

    def create_job(self, tool_type: str, input_files: list[str | Path], output_folder: str | Path, **options: Any) -> dict[str, object]:
        try:
            job = self.job_manager.create_job(ToolType(tool_type), input_files, output_folder, **options)
            return {"success": True, "message": "Job berhasil dibuat.", "job_id": job.job_id, "data": job_to_view_model(job)}
        except Exception as exc:
            return {"success": False, "message": self._message(exc), "job_id": None, "data": {}}

    def start_job(self, job_id: str) -> dict[str, object]:
        try:
            self.job_manager.start_job(job_id)
            return {"success": True, "message": "Proses berhasil dimulai.", "job_id": job_id, "data": {}}
        except Exception as exc:
            return {"success": False, "message": self._message(exc), "job_id": job_id, "data": {}}

    def cancel_job(self, job_id: str) -> dict[str, object]:
        try:
            self.job_manager.cancel_job(job_id)
            return {"success": True, "message": "Permintaan batal dikirim.", "job_id": job_id, "data": {}}
        except Exception as exc:
            return {"success": False, "message": self._message(exc), "job_id": job_id, "data": {}}

    def get_job_status(self, job_id: str) -> dict[str, object]:
        try:
            job = self.job_manager.get_job(job_id)
            return {"success": True, "message": "Status job berhasil diambil.", "job_id": job_id, "data": job_to_view_model(job)}
        except Exception as exc:
            return {"success": False, "message": self._message(exc), "job_id": job_id, "data": {}}

    def list_history(self, limit: int = 50, status: str | None = None) -> dict[str, object]:
        try:
            return {"success": True, "message": "Riwayat berhasil diambil.", "job_id": None, "data": {"items": self.job_manager.list_history(limit, status)}}
        except Exception as exc:
            return {"success": False, "message": self._message(exc), "job_id": None, "data": {"items": []}}

    def clear_history(self) -> dict[str, object]:
        self.job_manager.clear_history()
        return {"success": True, "message": "Riwayat berhasil dihapus.", "job_id": None, "data": {}}

    def _message(self, exc: Exception) -> str:
        if isinstance(exc, AppError):
            return str(exc)
        return f"Terjadi kesalahan: {exc}"
