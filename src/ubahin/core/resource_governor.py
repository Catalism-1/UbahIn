from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import psutil

from ubahin.core.error_codes import ErrorCode
from ubahin.core.models import AppError, PerformanceMode
from ubahin.native_bridge import system_snapshot
from ubahin.utils import available_disk_bytes


@dataclass(slots=True)
class ResourceSnapshot:
    logical_cpu_count: int
    cpu_percent: float
    available_memory: int
    total_memory: int
    available_disk: int
    battery_percent: float | None = None
    power_plugged: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_cpu_count": self.logical_cpu_count,
            "cpu_percent": self.cpu_percent,
            "available_memory": self.available_memory,
            "total_memory": self.total_memory,
            "available_disk": self.available_disk,
            "battery_percent": self.battery_percent,
            "power_plugged": self.power_plugged,
        }


class ResourceGovernor:
    def __init__(
        self,
        min_available_memory: int = 512 * 1024 * 1024,
        high_cpu_threshold: float = 92.0,
    ) -> None:
        self.min_available_memory = min_available_memory
        self.high_cpu_threshold = high_cpu_threshold

    def snapshot(self, output_dir: Path | None = None) -> ResourceSnapshot:
        native = system_snapshot(output_dir)
        memory = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        return ResourceSnapshot(
            logical_cpu_count=int(native.get("logical_cpu_count") or (os.cpu_count() or 1)),
            cpu_percent=psutil.cpu_percent(interval=0.05),
            available_memory=int(native.get("available_memory") or memory.available),
            total_memory=int(native.get("total_memory") or memory.total),
            available_disk=int(native.get("available_disk") or available_disk_bytes(output_dir or Path.cwd())),
            battery_percent=battery.percent if battery else None,
            power_plugged=battery.power_plugged if battery else None,
        )

    def effective_mode(self, requested: PerformanceMode, snapshot: ResourceSnapshot) -> PerformanceMode:
        if snapshot.available_memory < self.min_available_memory:
            return PerformanceMode.RAM_SAVER
        if requested == PerformanceMode.FAST:
            if snapshot.logical_cpu_count < 4 or snapshot.cpu_percent >= 80 or snapshot.available_memory < 2 * 1024 * 1024 * 1024:
                return PerformanceMode.BALANCED
        if requested == PerformanceMode.BALANCED and snapshot.available_memory < 1 * 1024 * 1024 * 1024:
            return PerformanceMode.RAM_SAVER
        return requested

    def worker_count(self, requested: PerformanceMode, snapshot: ResourceSnapshot) -> int:
        mode = self.effective_mode(requested, snapshot)
        if mode == PerformanceMode.RAM_SAVER:
            return 1
        if mode == PerformanceMode.BALANCED:
            return min(2, max(1, snapshot.logical_cpu_count - 1))
        return min(4, max(1, snapshot.logical_cpu_count - 1))

    def ensure_enough_disk(self, output_dir: Path, required_bytes: int) -> None:
        free = available_disk_bytes(output_dir)
        if free < int(required_bytes * 1.1):
            raise AppError("Ruang penyimpanan tidak cukup untuk perkiraan hasil.", ErrorCode.INSUFFICIENT_DISK_SPACE)

    def wait_for_resources(self, requested: PerformanceMode, output_dir: Path, timeout_seconds: float = 30.0) -> ResourceSnapshot:
        deadline = time.monotonic() + timeout_seconds
        last_snapshot = self.snapshot(output_dir)
        while time.monotonic() < deadline:
            last_snapshot = self.snapshot(output_dir)
            if last_snapshot.available_memory >= self.min_available_memory and last_snapshot.cpu_percent < self.high_cpu_threshold:
                return last_snapshot
            time.sleep(0.5)
        if last_snapshot.available_memory < self.min_available_memory:
            raise AppError("Memori bebas terlalu rendah. Coba mode Hemat RAM atau tutup aplikasi lain.", ErrorCode.OUT_OF_MEMORY_RISK)
        return last_snapshot
