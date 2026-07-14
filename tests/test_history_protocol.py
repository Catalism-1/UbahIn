from __future__ import annotations

import sqlite3
from pathlib import Path

from ubahin.services.history_service import HistoryService


def _seed(connection: sqlite3.Connection, job_id: str, status: str, tool: str, created: str, warnings: int = 0) -> None:
    connection.execute(
        """
        INSERT INTO history
        (job_id, tool_type, main_file, input_count, output_count, output_dir, status,
         created_at, started_at, finished_at, duration, error_summary, input_size, output_size, warning_count)
        VALUES (?, ?, ?, 1, 2, 'C:/out', ?, ?, ?, ?, 1.0, '', 100, 200, ?)
        """,
        (job_id, tool, f"{job_id}.pdf", status, created, created, created, warnings),
    )


def test_serialized_fields(tmp_path: Path) -> None:
    service = HistoryService(tmp_path / "history.sqlite3")
    with service._connect() as connection:  # noqa: SLF001
        _seed(connection, "a", "completed", "pdf_to_jpg", "2026-01-01T10:00:00")
    item = service.list_history()["items"][0]
    expected_keys = {
        "id",
        "tool_type",
        "status",
        "created_at",
        "started_at",
        "ended_at",
        "duration_seconds",
        "primary_filename",
        "input_count",
        "output_count",
        "output_directory",
        "input_size_bytes",
        "output_size_bytes",
        "error_summary",
        "warning_count",
    }
    assert expected_keys == set(item.keys())
    assert item["id"] == "a"
    assert item["output_directory"] == "C:/out"


def test_status_filter_groups_warnings(tmp_path: Path) -> None:
    service = HistoryService(tmp_path / "history.sqlite3")
    with service._connect() as connection:  # noqa: SLF001
        _seed(connection, "ok", "completed", "pdf_to_jpg", "2026-01-01T10:00:00")
        _seed(connection, "warn", "completed_with_warnings", "pdf_to_jpg", "2026-01-01T10:01:00", warnings=2)
        _seed(connection, "bad", "failed", "pdf_to_jpg", "2026-01-01T10:02:00")
        _seed(connection, "stop", "cancelled", "pdf_to_jpg", "2026-01-01T10:03:00")

    completed = service.list_history(status="completed")
    assert completed["total"] == 2
    assert {item["status"] for item in completed["items"]} == {"completed", "completed_with_warnings"}
    assert service.list_history(status="failed")["total"] == 1
    assert service.list_history(status="cancelled")["total"] == 1
    assert service.list_history(status="all")["total"] == 4


def test_pagination_and_recent(tmp_path: Path) -> None:
    service = HistoryService(tmp_path / "history.sqlite3")
    with service._connect() as connection:  # noqa: SLF001
        for index in range(7):
            _seed(connection, f"job-{index}", "completed", "pdf_to_jpg", f"2026-01-01T10:0{index}:00")
    page = service.list_history(limit=5, offset=0)
    assert len(page["items"]) == 5
    assert page["has_more"] is True
    page_two = service.list_history(limit=5, offset=5)
    assert len(page_two["items"]) == 2
    assert page_two["has_more"] is False
    recent = service.get_recent(limit=3)
    assert [item["id"] for item in recent] == ["job-6", "job-5", "job-4"]


def test_delete_keeps_other_records(tmp_path: Path) -> None:
    service = HistoryService(tmp_path / "history.sqlite3")
    with service._connect() as connection:  # noqa: SLF001
        _seed(connection, "a", "completed", "pdf_to_jpg", "2026-01-01T10:00:00")
        _seed(connection, "b", "completed", "pdf_to_jpg", "2026-01-01T10:01:00")
    assert service.delete("a") is True
    assert service.delete("missing") is False
    remaining = service.list_history()
    assert remaining["total"] == 1
    assert remaining["items"][0]["id"] == "b"


def test_retention_keeps_newest_500(tmp_path: Path) -> None:
    service = HistoryService(tmp_path / "history.sqlite3", retention_limit=500)
    connection = service._connect()  # noqa: SLF001
    with connection:
        for index in range(505):
            _seed(connection, f"job-{index:04d}", "completed", "pdf_to_jpg", f"2026-01-01T00:00:{index:04d}")
        service._apply_retention(connection)  # noqa: SLF001
    connection.close()
    assert service.list_history(limit=1)["total"] == 500


def test_legacy_v1_migration(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    connection.execute(
        """
        CREATE TABLE history (
            job_id TEXT PRIMARY KEY, tool_type TEXT NOT NULL, main_file TEXT, input_count INTEGER NOT NULL,
            output_count INTEGER NOT NULL, output_dir TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT,
            finished_at TEXT, duration REAL, error_summary TEXT, input_size INTEGER NOT NULL, output_size INTEGER NOT NULL
        )
        """
    )
    connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")
    connection.execute(
        "INSERT INTO history VALUES ('old', 'pdf_to_jpg', 'Lama.pdf', 1, 3, 'C:/out', 'completed',"
        " '2026-01-01T10:00:00', '2026-01-01T10:00:05', 5.0, '', 1000, 3000)"
    )
    connection.commit()
    connection.close()

    service = HistoryService(database)
    item = service.list_history()["items"][0]
    assert item["id"] == "old"
    assert item["created_at"] == "2026-01-01T10:00:00"  # diisi dari started_at
    assert item["warning_count"] == 0
    # backup database lama dibuat sebelum migrasi
    assert database.with_suffix(".sqlite3.v1.bak").exists()
