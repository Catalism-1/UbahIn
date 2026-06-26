from __future__ import annotations

from pathlib import Path

from ubahin.desktop.bridge import DesktopBridge


def test_clear_selected_files_returns_serializable_ok() -> None:
    bridge = DesktopBridge()
    bridge._selected_files["file-1"] = {"id": "file-1", "name": "sample.pdf"}

    result = bridge.clear_selected_files()

    assert result == {"success": True, "message": "", "data": {}}
    assert bridge._selected_files == {}


def test_log_frontend_writes_frontend_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("ubahin.desktop.bridge.get_log_dir", lambda: tmp_path)
    bridge = DesktopBridge()

    result = bridge.log_frontend(
        {
            "level": "error",
            "action": "bridge.clear_selected_files",
            "route": "pdf",
            "bridgeReady": True,
            "loading": {"active": False},
            "activeModal": None,
            "error": "timeout",
        }
    )

    assert result["success"] is True
    log_text = (tmp_path / "frontend.log").read_text(encoding="utf-8")
    assert "bridge.clear_selected_files" in log_text
    assert "timeout" in log_text
