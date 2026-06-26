from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ubahin.core.models import PerformanceMode
from ubahin.utils import app_data_dir


@dataclass(slots=True)
class AppSettings:
    theme: str = "system"
    default_output_dir: str = ""
    performance_mode: PerformanceMode = PerformanceMode.BALANCED
    default_jpg_quality: int = 90
    default_dpi: int = 200
    notify_on_completion: bool = True
    open_output_after_finish: bool = False
    auto_zip_after_finish: bool = False

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["performance_mode"] = self.performance_mode.value
        return data


class SettingsService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "settings" / "settings.json"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return AppSettings(
                theme=str(raw.get("theme", "system")),
                default_output_dir=str(raw.get("default_output_dir", "")),
                performance_mode=PerformanceMode(raw.get("performance_mode", "seimbang")),
                default_jpg_quality=int(raw.get("default_jpg_quality", 90)),
                default_dpi=int(raw.get("default_dpi", 200)),
                notify_on_completion=bool(raw.get("notify_on_completion", True)),
                open_output_after_finish=bool(raw.get("open_output_after_finish", False)),
                auto_zip_after_finish=bool(raw.get("auto_zip_after_finish", False)),
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(settings.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
