from __future__ import annotations

import json
from pathlib import Path

from ubahin.core import PerformanceMode
from ubahin.services.settings_service import AppSettings, SettingsService


def test_protocol_roundtrip_and_validation(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    payload = {
        "theme": "light",
        "default_output_directory": "C:/Hasil Ubahin",
        "performance_mode": "balanced",
        "default_pdf_preset": "high",
        "default_dpi": 99999,  # di luar batas -> clamp ke maksimum
        "default_jpeg_quality": "80",  # string -> int
        "create_zip_after_conversion": True,
        "open_output_after_finish": False,
        "notifications_enabled": "ya",
    }
    service.save(AppSettings.from_protocol_payload(payload))
    loaded = service.load().to_protocol_dict()

    assert loaded["theme"] == "light"
    assert loaded["default_pdf_preset"] == "high"
    assert loaded["default_dpi"] == 600
    assert loaded["default_jpeg_quality"] == 80
    assert loaded["create_zip_after_conversion"] is True
    assert loaded["notifications_enabled"] is True
    assert loaded["performance_mode"] == "balanced"


def test_save_is_atomic_and_versioned(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    service = SettingsService(path)
    service.save(AppSettings(performance_mode=PerformanceMode.FAST))
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["version"] == 2
    assert document["settings"]["performance_mode"] == "fast"
    # tidak ada file temporer tersisa setelah penulisan atomic
    assert not list(tmp_path.glob(".settings.json.tmp"))


def test_corrupt_file_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    service = SettingsService(path)
    settings = service.load()
    assert settings.theme == "system"
    assert settings.default_dpi == 150


def test_invalid_enum_uses_safe_default() -> None:
    settings = AppSettings.from_protocol_payload({"theme": "rainbow", "performance_mode": "turbo"})
    assert settings.theme == "system"
    assert settings.performance_mode == PerformanceMode.BALANCED
