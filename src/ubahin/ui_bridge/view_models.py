from __future__ import annotations

from ubahin.core.job import Job


def job_to_view_model(job: Job) -> dict[str, object]:
    return job.to_dict()
