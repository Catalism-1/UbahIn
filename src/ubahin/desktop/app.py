"""Desktop entry point for the native pywebview-hosted Ubahin UI."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ubahin.desktop.self_check import main as self_check_main
from ubahin.desktop.startup import show_startup_error_dialog, write_startup_exception
from ubahin.desktop.window_manager import create_main_window
from ubahin.utils import get_resource_path, setup_logging


def _web_root() -> Path:
    """Locate the bundled web directory in source and frozen builds."""
    candidates = [
        Path(__file__).resolve().parent / "web",
        get_resource_path("src/ubahin/desktop/web"),
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_root = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        candidates.extend(
            [
                bundle_root / "ubahin" / "desktop" / "web",
                bundle_root / "src" / "ubahin" / "desktop" / "web",
            ]
        )
    for candidate in candidates:
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate
    raise FileNotFoundError("Folder web Ubahin tidak ditemukan. Build mungkin tidak menyertakan asset UI.")


def launch_desktop_shell() -> int:
    """Start Ubahin as a native desktop window with a bundled local UI."""
    setup_logging()
    try:
        import webview
    except Exception as exc:
        log_path = write_startup_exception(exc)
        show_startup_error_dialog(log_path)
        return 1

    from ubahin.desktop.bridge import DesktopBridge

    bridge: DesktopBridge | None = None
    try:
        index_html = _web_root() / "index.html"
        bridge = DesktopBridge()
        window = create_main_window(webview, index_html, bridge)
        if window is None:
            raise RuntimeError("PyWebView gagal membuat window utama Ubahin.")
        bridge.attach_window(window)
        webview.start(debug=os.environ.get("UBAHIN_DEBUG_WEBVIEW") == "1")
        return 0
    except Exception as exc:
        log_path = write_startup_exception(exc)
        show_startup_error_dialog(log_path)
        return 1
    finally:
        if bridge is not None:
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
