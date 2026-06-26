from __future__ import annotations

from pathlib import Path

from ubahin.desktop.self_check import run_self_check
from ubahin.utils import get_app_data_dir, get_log_dir


def test_desktop_self_check_uses_writable_app_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    report = run_self_check()
    assert report.ok
    assert Path(report.app_data_dir) == tmp_path / "Ubahin"
    assert Path(report.log_dir) == tmp_path / "Ubahin" / "logs"
    assert get_app_data_dir() == tmp_path / "Ubahin"
    assert get_log_dir() == tmp_path / "Ubahin" / "logs"
