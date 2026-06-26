from __future__ import annotations

from pathlib import Path

from ubahin.core import JobManager, JobStatus
from ubahin.services import HistoryService


def test_history_database(sample_pdf: Path, tmp_path: Path) -> None:
    history = HistoryService(tmp_path / "history.sqlite3")
    manager = JobManager(history_service=history)
    job = manager.create_job("pdf_to_jpg", [sample_pdf], tmp_path / "out", dpi=120, jpg_quality=80)
    manager.start_job(job.job_id)
    assert manager.wait(job.job_id, timeout=10)
    assert manager.get_job_status(job.job_id) == JobStatus.COMPLETED
    assert (tmp_path / "out" / "conversion_log.txt").exists()
    rows = history.list_recent()
    assert len(rows) == 1
    assert rows[0]["tool_type"] == "pdf_to_jpg"
    history.delete(job.job_id)
    assert history.list_recent() == []


def test_history_migration_and_retention(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    service = HistoryService(database, retention_limit=1)
    assert service.list_recent() == []
    with service._connect() as connection:  # noqa: SLF001 - intentional schema smoke test
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    assert rows[0]["version"] == 1
