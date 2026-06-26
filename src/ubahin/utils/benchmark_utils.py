from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import psutil


@dataclass(slots=True)
class BenchmarkResult:
    name: str
    duration_seconds: float
    memory_rss_bytes: int


@contextmanager
def benchmark(name: str) -> Iterator[list[BenchmarkResult]]:
    process = psutil.Process()
    start = time.monotonic()
    holder: list[BenchmarkResult] = []
    try:
        yield holder
    finally:
        holder.append(
            BenchmarkResult(
                name=name,
                duration_seconds=time.monotonic() - start,
                memory_rss_bytes=process.memory_info().rss,
            )
        )
