from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ubahin.core.models import PerformanceMode
from ubahin.utils import app_data_dir

# Versi schema settings. Naikkan ketika format file berubah agar migrasi aman.
SETTINGS_SCHEMA = "ubahin.settings"
SETTINGS_VERSION = 2

VALID_THEMES = ("light", "dark", "system")
VALID_PRESETS = ("standard", "high", "ultra")

# Token performa di "kabel" (wire) memakai bahasa Inggris agar konsisten dengan
# React dan engine. PerformanceMode internal memakai nilai bahasa Indonesia.
_WIRE_TO_MODE = {
    "ram_saver": PerformanceMode.RAM_SAVER,
    "memory_saver": PerformanceMode.RAM_SAVER,
    "hemat_ram": PerformanceMode.RAM_SAVER,
    "balanced": PerformanceMode.BALANCED,
    "seimbang": PerformanceMode.BALANCED,
    "fast": PerformanceMode.FAST,
    "cepat": PerformanceMode.FAST,
}
_MODE_TO_WIRE = {
    PerformanceMode.RAM_SAVER: "ram_saver",
    PerformanceMode.BALANCED: "balanced",
    PerformanceMode.FAST: "fast",
}

# Batas aman untuk angka agar nilai rusak tidak merusak konversi.
DPI_MIN, DPI_MAX = 72, 600
QUALITY_MIN, QUALITY_MAX = 40, 100


def _clamp_int(value: object, default: int, low: int, high: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "ya", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


@dataclass(slots=True)
class AppSettings:
    """Preferensi global Ubahin.

    Nama field internal sengaja dipertahankan agar kode lama (desktop bridge)
    tetap berjalan. Mapping ke nama protokol (wire) dilakukan lewat
    ``to_protocol_dict`` / ``from_protocol_payload``.
    """

    theme: str = "system"
    default_output_dir: str = ""
    performance_mode: PerformanceMode = PerformanceMode.BALANCED
    default_pdf_preset: str = "standard"
    default_dpi: int = 150
    default_jpg_quality: int = 80
    auto_zip_after_finish: bool = False
    open_output_after_finish: bool = True
    notify_on_completion: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "theme": self.theme,
            "default_output_dir": self.default_output_dir,
            "performance_mode": self.performance_mode.value,
            "default_pdf_preset": self.default_pdf_preset,
            "default_dpi": self.default_dpi,
            "default_jpg_quality": self.default_jpg_quality,
            "auto_zip_after_finish": self.auto_zip_after_finish,
            "open_output_after_finish": self.open_output_after_finish,
            "notify_on_completion": self.notify_on_completion,
        }

    def to_protocol_dict(self) -> dict[str, object]:
        """Bentuk yang dikirim ke Rust/React (nama field protokol)."""
        return {
            "theme": self.theme,
            "default_output_directory": self.default_output_dir,
            "performance_mode": _MODE_TO_WIRE.get(self.performance_mode, "balanced"),
            "default_pdf_preset": self.default_pdf_preset,
            "default_dpi": self.default_dpi,
            "default_jpeg_quality": self.default_jpg_quality,
            "create_zip_after_conversion": self.auto_zip_after_finish,
            "open_output_after_finish": self.open_output_after_finish,
            "notifications_enabled": self.notify_on_completion,
        }

    @classmethod
    def from_protocol_payload(cls, raw: dict[str, Any] | None) -> "AppSettings":
        """Bangun AppSettings dari payload protokol dengan validasi penuh.

        Field yang hilang atau rusak memakai default aman, tidak melempar error.
        """
        data = raw if isinstance(raw, dict) else {}
        defaults = cls()

        theme = str(data.get("theme", defaults.theme)).lower()
        if theme not in VALID_THEMES:
            theme = defaults.theme

        preset = str(data.get("default_pdf_preset", defaults.default_pdf_preset)).lower()
        if preset not in VALID_PRESETS:
            preset = defaults.default_pdf_preset

        mode = _WIRE_TO_MODE.get(str(data.get("performance_mode", "")).lower(), PerformanceMode.BALANCED)

        return cls(
            theme=theme,
            default_output_dir=str(data.get("default_output_directory", defaults.default_output_dir) or ""),
            performance_mode=mode,
            default_pdf_preset=preset,
            default_dpi=_clamp_int(data.get("default_dpi"), defaults.default_dpi, DPI_MIN, DPI_MAX),
            default_jpg_quality=_clamp_int(
                data.get("default_jpeg_quality"), defaults.default_jpg_quality, QUALITY_MIN, QUALITY_MAX
            ),
            auto_zip_after_finish=_coerce_bool(data.get("create_zip_after_conversion"), defaults.auto_zip_after_finish),
            open_output_after_finish=_coerce_bool(data.get("open_output_after_finish"), defaults.open_output_after_finish),
            notify_on_completion=_coerce_bool(data.get("notifications_enabled"), defaults.notify_on_completion),
        )


class SettingsService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "settings" / "settings.json"

    def load(self) -> AppSettings:
        """Muat settings. Default aman bila file belum ada atau rusak."""
        if not self.path.exists():
            return AppSettings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return AppSettings()
        if not isinstance(raw, dict):
            return AppSettings()

        # Format baru menyimpan field di bawah "settings"; format lama menyimpan datar.
        body = raw.get("settings") if isinstance(raw.get("settings"), dict) else raw
        defaults = AppSettings()
        try:
            mode_raw = str(body.get("performance_mode", "seimbang")).lower()
            mode = _WIRE_TO_MODE.get(mode_raw, defaults.performance_mode)
            preset = str(body.get("default_pdf_preset", defaults.default_pdf_preset)).lower()
            if preset not in VALID_PRESETS:
                preset = defaults.default_pdf_preset
            theme = str(body.get("theme", defaults.theme)).lower()
            if theme not in VALID_THEMES:
                theme = defaults.theme
            return AppSettings(
                theme=theme,
                # Dukung nama protokol baru dan nama internal lama.
                default_output_dir=str(
                    body.get("default_output_directory", body.get("default_output_dir", defaults.default_output_dir))
                    or ""
                ),
                performance_mode=mode,
                default_pdf_preset=preset,
                default_dpi=_clamp_int(body.get("default_dpi"), defaults.default_dpi, DPI_MIN, DPI_MAX),
                default_jpg_quality=_clamp_int(
                    body.get("default_jpeg_quality", body.get("default_jpg_quality")),
                    defaults.default_jpg_quality,
                    QUALITY_MIN,
                    QUALITY_MAX,
                ),
                auto_zip_after_finish=_coerce_bool(
                    body.get("create_zip_after_conversion", body.get("auto_zip_after_finish")),
                    defaults.auto_zip_after_finish,
                ),
                open_output_after_finish=_coerce_bool(
                    body.get("open_output_after_finish"), defaults.open_output_after_finish
                ),
                notify_on_completion=_coerce_bool(
                    body.get("notifications_enabled", body.get("notify_on_completion")),
                    defaults.notify_on_completion,
                ),
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        """Simpan settings secara atomic (tulis ke temp lalu rename)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "schema": SETTINGS_SCHEMA,
            "version": SETTINGS_VERSION,
            # Simpan dengan nama protokol agar konsisten dengan React/Rust.
            "settings": settings.to_protocol_dict(),
        }
        payload = json.dumps(document, indent=2, ensure_ascii=False)
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, self.path)
