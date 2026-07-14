from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any

from ubahin.core.job import Job
from ubahin.utils import app_data_dir

# Versi schema database riwayat. Migrasi dilakukan secara berurutan & transaksional.
HISTORY_SCHEMA_VERSION = 2

# Kelompok status agar filter "Berhasil" mencakup selesai dengan peringatan.
_STATUS_GROUPS: dict[str, tuple[str, ...]] = {
    "completed": ("completed", "completed_with_warnings"),
    "failed": ("failed",),
    "cancelled": ("cancelled",),
}


class HistoryService:
    def __init__(self, database_path: Path | None = None, retention_limit: int = 500) -> None:
        self.database_path = database_path or app_data_dir() / "history" / "history.sqlite3"
        self.retention_limit = retention_limit
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    # ------------------------------------------------------------------ schema
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
        self._migrate()

    def _current_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
        return int(row["version"] or 1) if row else 1

    def _columns(self, connection: sqlite3.Connection) -> set[str]:
        return {str(row["name"]) for row in connection.execute("PRAGMA table_info(history)").fetchall()}

    def _backup_database(self, version: int) -> None:
        if not self.database_path.exists():
            return
        backup = self.database_path.with_suffix(self.database_path.suffix + f".v{version}.bak")
        try:
            shutil.copy2(self.database_path, backup)
        except OSError:
            # Backup gagal bukan alasan untuk membatalkan; migrasi tetap transaksional.
            pass

    def _migrate(self) -> None:
        if self._current_version() >= HISTORY_SCHEMA_VERSION:
            return
        # Backup database lama sebelum migrasi besar agar dapat dipulihkan.
        self._backup_database(self._current_version())
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            columns = self._columns(connection)
            if "created_at" not in columns:
                connection.execute("ALTER TABLE history ADD COLUMN created_at TEXT")
                connection.execute(
                    "UPDATE history SET created_at = COALESCE(started_at, finished_at) WHERE created_at IS NULL"
                )
            if "warning_count" not in columns:
                connection.execute("ALTER TABLE history ADD COLUMN warning_count INTEGER NOT NULL DEFAULT 0")
            connection.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (2)")
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    # -------------------------------------------------------------------- write
    def save_job(self, job: Job) -> None:
        input_size = sum(path.stat().st_size for path in job.input_files if path.exists())
        output_paths = job.result.output_paths if job.result else []
        output_size = sum(path.stat().st_size for path in output_paths if path.exists())
        warning_count = len(job.warnings)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO history
                (job_id, tool_type, main_file, input_count, output_count, output_dir, status,
                 created_at, started_at, finished_at, duration, error_summary, input_size, output_size,
                 warning_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    output_count=excluded.output_count,
                    status=excluded.status,
                    finished_at=excluded.finished_at,
                    duration=excluded.duration,
                    error_summary=excluded.error_summary,
                    output_size=excluded.output_size,
                    warning_count=excluded.warning_count
                """,
                (
                    job.job_id,
                    job.tool_type.value,
                    job.input_files[0].name if job.input_files else "",
                    len(job.input_files),
                    len(output_paths),
                    str(job.options.output_dir),
                    job.status.value,
                    job.created_at.isoformat() if job.created_at else None,
                    job.start_time.isoformat() if job.start_time else None,
                    job.end_time.isoformat() if job.end_time else None,
                    job.duration,
                    "; ".join((job.errors or job.warnings)[:3]),
                    input_size,
                    output_size,
                    warning_count,
                ),
            )
            self._apply_retention(connection)

    # --------------------------------------------------------------------- read
    def list_recent(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        """Daftar baris mentah (dipakai kode lama dan self check)."""
        query = "SELECT * FROM history"
        params: list[object] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY COALESCE(created_at, started_at, finished_at, '') DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def list_history(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        tool_type: str | None = None,
    ) -> dict[str, Any]:
        """Daftar riwayat dengan paginasi & filter, bentuk siap protokol."""
        limit = max(1, min(int(limit or 50), 500))
        offset = max(0, int(offset or 0))
        where, params = self._build_filters(status, tool_type)

        count_sql = "SELECT COUNT(*) AS total FROM history"
        list_sql = "SELECT * FROM history"
        if where:
            count_sql += f" WHERE {where}"
            list_sql += f" WHERE {where}"
        list_sql += " ORDER BY COALESCE(created_at, started_at, finished_at, '') DESC LIMIT ? OFFSET ?"

        with self._connect() as connection:
            total = int(connection.execute(count_sql, params).fetchone()["total"])
            rows = connection.execute(list_sql, [*params, limit, offset]).fetchall()

        items = [self._serialize(row) for row in rows]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        }

    def get_recent(self, limit: int = 5) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 5), 50))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM history ORDER BY COALESCE(created_at, started_at, finished_at, '') DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._serialize(row) for row in rows]

    def get_output_dir(self, job_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT output_dir FROM history WHERE job_id = ?", (job_id,)).fetchone()
        return str(row["output_dir"]) if row else None

    # ------------------------------------------------------------------- delete
    def delete(self, job_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM history WHERE job_id = ?", (job_id,))
            return cursor.rowcount > 0

    def clear(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM history")
            return cursor.rowcount

    # ------------------------------------------------------------------ helpers
    def _build_filters(self, status: str | None, tool_type: str | None) -> tuple[str, list[object]]:
        clauses: list[str] = []
        params: list[object] = []
        normalized_status = (status or "all").lower()
        if normalized_status not in {"all", ""}:
            group = _STATUS_GROUPS.get(normalized_status)
            if group:
                placeholders = ", ".join("?" for _ in group)
                clauses.append(f"status IN ({placeholders})")
                params.extend(group)
            else:
                clauses.append("status = ?")
                params.append(normalized_status)
        normalized_tool = (tool_type or "all").lower()
        if normalized_tool not in {"all", ""}:
            clauses.append("tool_type = ?")
            params.append(normalized_tool)
        return " AND ".join(clauses), params

    def _serialize(self, row: sqlite3.Row) -> dict[str, Any]:
        keys = row.keys()
        return {
            "id": row["job_id"],
            "tool_type": row["tool_type"],
            "status": row["status"],
            "created_at": (row["created_at"] if "created_at" in keys else None) or row["started_at"],
            "started_at": row["started_at"],
            "ended_at": row["finished_at"],
            "duration_seconds": row["duration"],
            "primary_filename": row["main_file"] or "",
            "input_count": row["input_count"],
            "output_count": row["output_count"],
            "output_directory": row["output_dir"],
            "input_size_bytes": row["input_size"],
            "output_size_bytes": row["output_size"],
            "error_summary": row["error_summary"] or "",
            "warning_count": row["warning_count"] if "warning_count" in keys else 0,
        }

    def _apply_retention(self, connection: sqlite3.Connection) -> None:
        if self.retention_limit <= 0:
            return
        # Simpan hanya N record terbaru; hapus yang tertua bila melewati batas.
        connection.execute(
            """
            DELETE FROM history
            WHERE job_id NOT IN (
                SELECT job_id FROM history
                ORDER BY COALESCE(created_at, started_at, finished_at, '') DESC
                LIMIT ?
            )
            """,
            (self.retention_limit,),
        )
