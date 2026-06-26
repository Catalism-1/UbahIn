from __future__ import annotations

from pathlib import Path

from ubahin.core import JobManager, JobStatus
from ubahin.services import HistoryService


def test_job_lifecycle_api(sample_pdf: Path, tmp_path: Path) -> None:
    manager = JobManager(history_service=HistoryService(tmp_path / "history.sqlite3"))
    job = manager.create_job("pdf_to_jpg", [sample_pdf], tmp_path / "out", dpi=120, jpg_quality=80)
    manager.queue_job(job.job_id)
    assert manager.get_active_jobs()
    manager.start_job(job.job_id)
    assert manager.wait_for_job(job.job_id, timeout=10)
    final = manager.get_job(job.job_id)
    assert final.status == JobStatus.COMPLETED
    assert final.resource_snapshot
    assert manager.get_job_progress(job.job_id).percentage >= 0
    assert manager.get_job_result(job.job_id) is not None
    assert manager.get_job_history()
