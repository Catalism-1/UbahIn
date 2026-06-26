from .cancellation import CancellationToken
from .error_codes import ErrorCode
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
from .resource_governor import ResourceGovernor, ResourceSnapshot


def __getattr__(name: str) -> object:
    if name == "JobManager":
        from .job_manager import JobManager

        return JobManager
    raise AttributeError(name)

__all__ = [
    "AppError",
    "CancellationToken",
    "ErrorCode",
    "FileResult",
    "Job",
    "JobManager",
    "JobOptions",
    "JobResult",
    "JobStatus",
    "PerformanceMode",
    "ProgressInfo",
    "ResourceGovernor",
    "ResourceSnapshot",
    "ServiceResult",
    "ToolType",
]
