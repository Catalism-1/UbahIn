from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ubahin.core.job import Job
from ubahin.utils import app_data_dir


class HistoryService:
    def __init__(self, database_path: Path | None = None, retention_limit: int = 500) -> None:
        self.database_path = database_path or app_data_dir() / "history.sqlite3"
        self.retention_limit = retention_limit
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    job_id TEXT PRIMARY KEY,
                    tool_type TEXT NOT NULL,
                    main_file TEXT,
                    input_count INTEGER NOT NULL,
                    output_count INTEGER NOT NULL,
                    output_dir TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    duration REAL,
                    error_summary TEXT,
                    input_size INTEGER NOT NULL,
                    output_size INTEGER NOT NULL
                )
                """
            )
            connection.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (1)")

    def save_job(self, job: Job) -> None:
        input_size = sum(path.stat().st_size for path in job.input_files if path.exists())
        output_paths = job.result.output_paths if job.result else []
        output_size = sum(path.stat().st_size for path in output_paths if path.exists())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO history
                (job_id, tool_type, main_file, input_count, output_count, output_dir, status,
                 started_at, finished_at, duration, error_summary, input_size, output_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    output_count=excluded.output_count,
                    status=excluded.status,
                    finished_at=excluded.finished_at,
                    duration=excluded.duration,
                    error_summary=excluded.error_summary,
                    output_size=excluded.output_size
                """,
                (
                    job.job_id,
                    job.tool_type.value,
                    job.input_files[0].name if job.input_files else "",
                    len(job.input_files),
                    len(output_paths),
                    str(job.options.output_dir),
                    job.status.value,
                    job.start_time.isoformat() if job.start_time else None,
                    job.end_time.isoformat() if job.end_time else None,
                    job.duration,
                    "; ".join(job.errors[:3]),
                    input_size,
                    output_size,
                ),
            )
            self._apply_retention(connection)

    def list_recent(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM history"
        params: list[object] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def delete(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM history WHERE job_id = ?", (job_id,))

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM history")

    def _apply_retention(self, connection: sqlite3.Connection) -> None:
        if self.retention_limit <= 0:
            return
        connection.execute(
            """
            DELETE FROM history
            WHERE job_id NOT IN (
                SELECT job_id FROM history
                ORDER BY COALESCE(started_at, finished_at, '') DESC
                LIMIT ?
            )
            """,
            (self.retention_limit,),
        )
