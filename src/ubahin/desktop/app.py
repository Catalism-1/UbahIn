"""Desktop entry point — pywebview shell that hosts the HTML/CSS/JS UI."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ubahin.desktop.self_check import main as self_check_main
from ubahin.desktop.startup import show_startup_error_dialog, write_startup_exception
from ubahin.utils import get_resource_path, setup_logging


def _web_root() -> Path:
    """Locate the bundled web/ directory both in dev and frozen builds."""
    candidates = [
        Path(__file__).resolve().parent / "web",
        get_resource_path("src/ubahin/desktop/web"),
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "ubahin" / "desktop" / "web")  # type: ignore[attr-defined]
        candidates.append(Path(sys._MEIPASS) / "src" / "ubahin" / "desktop" / "web")  # type: ignore[attr-defined]
    for candidate in candidates:
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate
    raise FileNotFoundError(
        "Folder web Ubahin tidak ditemukan. Build mungkin tidak menyertakan asset UI."
    )


def launch_desktop_shell() -> int:
    """Start the pywebview window. Returns process exit code."""
    setup_logging()
    try:
        import webview
    except Exception as exc:
        log_path = write_startup_exception(exc)
        show_startup_error_dialog(log_path)
        return 1

    from ubahin.desktop.bridge import DesktopBridge

    web_root = _web_root()
    index_html = web_root / "index.html"
    bridge = DesktopBridge()

    window = webview.create_window(
        title="Ubahin",
        url=str(index_html),
        js_api=bridge,
        width=1200,
        height=780,
        min_size=(1024, 640),
        background_color="#F8F7F4",
        text_select=False,
    )
    bridge.attach_window(window)

    def _on_loaded() -> None:  # pragma: no cover - GUI hook
        pass

    try:
        window.events.loaded += _on_loaded
    except Exception:
        pass

    debug = os.environ.get("UBAHIN_DEBUG_WEBVIEW") == "1"
    try:
        webview.start(debug=debug)
        return 0
    finally:
        bridge.detach_window()


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Ubahin", description="Launcher desktop Ubahin")
    parser.add_argument("--self-check", action="store_true", help="Jalankan pemeriksaan sistem internal.")
    parser.add_argument("--silent", action="store_true", help="Mode non-interaktif untuk pemeriksaan/build.")
    parser.add_argument("--json", action="store_true", help="Cetak laporan self-check dalam JSON.")
    args = parser.parse_args(argv)

    if args.self_check:
        self_args: list[str] = []
        if args.silent:
            self_args.append("--silent")
        if args.json:
            self_args.append("--json")
        return self_check_main(self_args)
    return launch_desktop_shell()


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(sys.argv[1:] if argv is None else argv)
    except SystemExit:
        raise
    except Exception as exc:
        log_path = write_startup_exception(exc)
        if argv is None and "--silent" not in sys.argv:
            show_startup_error_dialog(log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
