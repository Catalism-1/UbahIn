from __future__ import annotations

from pathlib import Path

from ubahin.core import PerformanceMode
from ubahin.core.resource_governor import ResourceGovernor, ResourceSnapshot


def test_resource_governor_downgrades_fast_when_memory_low(tmp_path: Path) -> None:
    governor = ResourceGovernor()
    snapshot = ResourceSnapshot(
        logical_cpu_count=2,
        cpu_percent=10,
        available_memory=256 * 1024 * 1024,
        total_memory=8 * 1024 * 1024 * 1024,
        available_disk=10 * 1024 * 1024 * 1024,
    )
    assert governor.effective_mode(PerformanceMode.FAST, snapshot) == PerformanceMode.RAM_SAVER


def test_resource_governor_snapshot(tmp_path: Path) -> None:
    snapshot = ResourceGovernor().snapshot(tmp_path)
    assert snapshot.logical_cpu_count >= 1
    assert snapshot.available_disk >= 0
