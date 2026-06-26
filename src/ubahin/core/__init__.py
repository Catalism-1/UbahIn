from .cancellation import CancellationToken
from .job import Job
from .models import (
    AppError,
    FileResult,
    JobOptions,
    JobResult,
    JobStatus,
    PerformanceMode,
    ServiceResult,
    ToolType,
)
from .progress import ProgressInfo


def __getattr__(name: str) -> object:
    if name == "JobManager":
        from .job_manager import JobManager

        return JobManager
    raise AttributeError(name)

__all__ = [
    "AppError",
    "CancellationToken",
    "FileResult",
    "Job",
    "JobManager",
    "JobOptions",
    "JobResult",
    "JobStatus",
    "PerformanceMode",
    "ProgressInfo",
    "ServiceResult",
    "ToolType",
]
