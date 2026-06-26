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
    status: JobStatus = JobStatus.PENDING
    progress: ProgressInfo = field(default_factory=ProgressInfo)
    start_time: datetime | None = None
    end_time: datetime | None = None
    errors: list[str] = field(default_factory=list)
    result: ServiceResult | None = None
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)

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
            "input_files": [str(path) for path in self.input_files],
            "output_folder": str(self.options.output_dir),
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "errors": list(self.errors),
            "result": {
                "output_paths": [str(path) for path in self.result.output_paths],
                "errors": list(self.result.errors),
                "message": self.result.message,
            }
            if self.result
            else None,
        }
