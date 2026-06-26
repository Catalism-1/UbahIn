from __future__ import annotations

from pathlib import Path

from ubahin.core import PerformanceMode
from ubahin.services import AppSettings, SettingsService


def test_settings_roundtrip(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    service.save(AppSettings(theme="dark", default_dpi=300, performance_mode=PerformanceMode.FAST))
    loaded = service.load()
    assert loaded.theme == "dark"
    assert loaded.default_dpi == 300
    assert loaded.performance_mode == PerformanceMode.FAST
