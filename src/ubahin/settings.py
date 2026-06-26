from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from .models import PerformanceMode
from .utils import app_data_dir


@dataclass(slots=True)
class AppSettings:
    theme: str = "system"
    language: str = "id"
    default_output_dir: str = ""
    performance_mode: PerformanceMode = PerformanceMode.BALANCED
    notify_on_completion: bool = True

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["performance_mode"] = self.performance_mode.value
        return data


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "settings.json"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return AppSettings(
                theme=str(raw.get("theme", "system")),
                language=str(raw.get("language", "id")),
                default_output_dir=str(raw.get("default_output_dir", "")),
                performance_mode=PerformanceMode(raw.get("performance_mode", "seimbang")),
                notify_on_completion=bool(raw.get("notify_on_completion", True)),
            )
        except (OSError, ValueError, json.JSONDecodeError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
