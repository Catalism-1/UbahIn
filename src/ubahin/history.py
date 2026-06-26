from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import ConversionJob
from .utils import app_data_dir


class HistoryStore:
    """Riwayat lokal SQLite agar GUI bisa menampilkan proses terdahulu."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or app_data_dir() / "history" / "history.sqlite3"
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
                CREATE TABLE IF NOT EXISTS conversion_history (
                    job_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )

    def save(self, job: ConversionJob) -> None:
        payload = job.to_dict()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversion_history
                    (job_id, created_at, finished_at, status, tool, output_dir, summary_json, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    finished_at=excluded.finished_at,
                    status=excluded.status,
                    summary_json=excluded.summary_json,
                    details_json=excluded.details_json
                """,
                (
                    job.job_id,
                    payload["created_at"],
                    payload["finished_at"],
                    job.status.value,
                    "pdf_to_jpg",
                    str(job.options.output_dir),
                    json.dumps(payload["summary"], ensure_ascii=False),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT job_id, created_at, finished_at, status, tool, output_dir, summary_json
                FROM conversion_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                **dict(row),
                "summary": json.loads(row["summary_json"]),
            }
            for row in rows
        ]

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM conversion_history")
