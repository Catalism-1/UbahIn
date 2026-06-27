from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .cancellation import CancellationToken
from .models import JobOptions, JobStatus, ServiceResult, ToolType, new_job_id, utc_now
from .progress import ProgressInfo


@dataclass(slots=True)
class Job:
    tool_type: ToolType
    input_files: list[Path]
    options: JobOptions
    job_id: str = field(default_factory=new_job_id)
    status: JobStatus = JobStatus.QUEUED
    priority: int = 0
    created_at: datetime = field(default_factory=utc_now)
    progress: ProgressInfo = field(default_factory=ProgressInfo)
    start_time: datetime | None = None
    end_time: datetime | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    result: ServiceResult | None = None
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    resource_snapshot: dict[str, object] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        if not self.start_time:
            return None
        end = self.end_time or utc_now()
        return (end - self.start_time).total_seconds()

    @property
    def output_folder(self) -> Path:
        return self.options.output_dir

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.job_id,
            "tool_type": self.tool_type.value,
            "created_at": self.created_at.isoformat(),
            "input_files": [str(path) for path in self.input_files],
            "output_folder": str(self.options.output_dir),
            "status": self.status.value,
            "priority": self.priority,
            "progress": self.progress.to_dict(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "performance_mode": self.options.performance_mode.value,
            "resource_snapshot": dict(self.resource_snapshot),
            "current_file": self.progress.current_file,
            "current_item": self.progress.current_item,
            "total_items": self.progress.total_items,
            "current_page": self.progress.current_page,
            "total_pages": self.progress.total_pages,
            "progress_percent": self.progress.percentage,
            "estimated_remaining_seconds": self.progress.estimated_remaining_seconds,
            "result_files": [str(path) for path in self.result.output_paths] if self.result else [],
            "result": {
                "output_paths": [str(path) for path in self.result.output_paths],
                "errors": list(self.result.errors),
                "warnings": list(self.result.warnings),
                "message": self.result.message,
                "successful_files": self.result.successful_files,
                "failed_files": self.result.failed_files,
                "skipped_files": self.result.skipped_files,
                "total_input_files": self.result.total_input_files,
                "processed_files": self.result.processed_files,
                "completed_files": self.result.completed_files,
            }
            if self.result
            else None,
        }
