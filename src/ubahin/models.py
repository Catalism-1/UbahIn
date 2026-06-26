from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class TaskStatus(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    CANCELLED = "cancelled"
    FAILED = "failed"


class QualityPreset(str, Enum):
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"

    @property
    def default_dpi(self) -> int:
        return {
            QualityPreset.STANDARD: 150,
            QualityPreset.HIGH: 200,
            QualityPreset.ULTRA: 300,
        }[self]

    @property
    def default_jpeg_quality(self) -> int:
        return {
            QualityPreset.STANDARD: 80,
            QualityPreset.HIGH: 90,
            QualityPreset.ULTRA: 95,
        }[self]


class PerformanceMode(str, Enum):
    RAM_SAVER = "hemat_ram"
    BALANCED = "seimbang"
    FAST = "cepat"


@dataclass(slots=True)
class ConversionOptions:
    output_dir: Path
    quality_preset: QualityPreset = QualityPreset.HIGH
    dpi: int | None = None
    jpeg_quality: int | None = None
    performance_mode: PerformanceMode = PerformanceMode.BALANCED
    create_zip: bool = False
    open_output_after_finish: bool = False
    optimize_file_size: bool = True
    white_document_background: bool = True
    max_files: int = 50

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir).expanduser().resolve()
        self.dpi = self.dpi or self.quality_preset.default_dpi
        self.jpeg_quality = self.jpeg_quality or self.quality_preset.default_jpeg_quality
        if self.dpi not in {120, 150, 200, 300}:
            raise ValueError("DPI harus salah satu dari: 120, 150, 200, atau 300.")
        if self.jpeg_quality not in {70, 80, 90, 95}:
            raise ValueError("Kualitas JPG harus salah satu dari: 70, 80, 90, atau 95.")
        if not 1 <= self.max_files <= 50:
            raise ValueError("Batas file harus berada di antara 1 dan 50.")


@dataclass(slots=True)
class FileTask:
    source_path: Path
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.QUEUED
    pages_total: int = 0
    pages_done: int = 0
    output_dir: Path | None = None
    output_files: list[Path] = field(default_factory=list)
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def filename(self) -> str:
        return self.source_path.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "source_path": str(self.source_path),
            "status": self.status.value,
            "pages_total": self.pages_total,
            "pages_done": self.pages_done,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "output_files": [str(path) for path in self.output_files],
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


@dataclass(slots=True)
class ConversionJob:
    tasks: list[FileTask]
    options: ConversionOptions
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    zip_path: Path | None = None
    error_message: str | None = None

    @property
    def total_pages(self) -> int:
        return sum(task.pages_total for task in self.tasks)

    @property
    def completed_pages(self) -> int:
        return sum(task.pages_done for task in self.tasks)

    @property
    def total_output_files(self) -> int:
        return sum(len(task.output_files) for task in self.tasks)

    @property
    def success_count(self) -> int:
        return sum(task.status == TaskStatus.COMPLETED for task in self.tasks)

    @property
    def failure_count(self) -> int:
        return sum(task.status == TaskStatus.FAILED for task in self.tasks)

    @property
    def cancelled_count(self) -> int:
        return sum(task.status == TaskStatus.CANCELLED for task in self.tasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "zip_path": str(self.zip_path) if self.zip_path else None,
            "error_message": self.error_message,
            "options": {
                **asdict(self.options),
                "output_dir": str(self.options.output_dir),
                "quality_preset": self.options.quality_preset.value,
                "performance_mode": self.options.performance_mode.value,
            },
            "summary": {
                "total_files": len(self.tasks),
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "cancelled_count": self.cancelled_count,
                "total_pages": self.total_pages,
                "completed_pages": self.completed_pages,
                "total_output_files": self.total_output_files,
            },
            "tasks": [task.to_dict() for task in self.tasks],
        }
