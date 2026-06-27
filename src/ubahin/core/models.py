from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class AppError(Exception):
    """Error yang aman ditampilkan untuk pengguna."""

    def __init__(self, message: str, code: object | None = None) -> None:
        super().__init__(message)
        self.code = code


class JobStatus(str, Enum):
    QUEUED = "queued"
    PENDING = "queued"
    VALIDATING = "validating"
    WAITING_FOR_RESOURCES = "waiting_for_resources"
    PROCESSING = "processing"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PerformanceMode(str, Enum):
    RAM_SAVER = "hemat_ram"
    BALANCED = "seimbang"
    FAST = "cepat"

    @property
    def max_workers(self) -> int:
        return {
            PerformanceMode.RAM_SAVER: 1,
            PerformanceMode.BALANCED: 2,
            PerformanceMode.FAST: 4,
        }[self]


class ToolType(str, Enum):
    PDF_TO_JPG = "pdf_to_jpg"
    IMAGE_TO_PDF = "image_to_pdf"
    MERGE_PDF = "merge_pdf"
    SPLIT_PDF = "split_pdf"
    COMPRESS_PDF = "compress_pdf"
    IMAGE_CONVERT = "image_convert"
    IMAGE_RESIZE = "image_resize"
    IMAGE_COMPRESS = "image_compress"


@dataclass(slots=True)
class JobOptions:
    output_dir: Path
    performance_mode: PerformanceMode = PerformanceMode.BALANCED
    create_zip: bool = False
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir).expanduser().resolve()
        if isinstance(self.performance_mode, str):
            self.performance_mode = PerformanceMode(self.performance_mode)


@dataclass(slots=True)
class FileResult:
    input_path: Path
    output_paths: list[Path] = field(default_factory=list)
    status: str = "completed"
    error: str | None = None
    input_size: int = 0
    output_size: int = 0


@dataclass(slots=True)
class ServiceResult:
    output_paths: list[Path] = field(default_factory=list)
    file_results: list[FileResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    message: str = ""
    total_input_files: int = 0
    processed_files: int = 0
    completed_files: int = 0

    @property
    def success(self) -> bool:
        return self.completed_files > 0 or any(file.status == "completed" for file in self.file_results)

    @property
    def successful_files(self) -> int:
        return sum(1 for file in self.file_results if file.status == "completed")

    @property
    def failed_files(self) -> int:
        return sum(1 for file in self.file_results if file.status == "failed")

    @property
    def skipped_files(self) -> int:
        return sum(1 for file in self.file_results if file.status == "skipped")

    @property
    def output_count(self) -> int:
        return len(self.output_paths)

    @property
    def output_size(self) -> int:
        return sum(path.stat().st_size for path in self.output_paths if path.exists())


@dataclass(slots=True)
class JobResult:
    job_id: str
    status: JobStatus
    result: ServiceResult | None = None
    errors: list[str] = field(default_factory=list)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_job_id() -> str:
    return str(uuid4())
