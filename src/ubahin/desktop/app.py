from __future__ import annotations

import argparse
import sys

from ubahin.desktop.main_window import MainWindow
from ubahin.desktop.self_check import main as self_check_main
from ubahin.desktop.startup import show_startup_error_dialog, write_startup_exception
from ubahin.utils import setup_logging


def launch_desktop_shell() -> int:
    setup_logging()
    app = MainWindow()
    app.run()
    return 0


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
