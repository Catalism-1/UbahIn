from __future__ import annotations

from pathlib import Path

from ubahin.desktop.window_manager import build_window_options


def test_window_options_use_local_file_native_shell(tmp_path: Path) -> None:
    index_html = tmp_path / "index.html"
    index_html.write_text("<!doctype html><title>Ubahin</title>", encoding="utf-8")

    options = build_window_options(index_html, bridge=object())

    assert options["title"] == "Ubahin"
    assert options["url"].startswith("file:///")
    assert "localhost" not in options["url"]
    assert not options["url"].startswith(("http://", "https://"))
    assert options["width"] == 1440
    assert options["height"] == 900
    assert options["min_size"] == (1100, 700)
    assert options["frameless"] is True
    assert options["text_select"] is False
    assert options["zoomable"] is False
