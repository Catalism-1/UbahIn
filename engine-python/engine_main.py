from __future__ import annotations

import argparse
import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any


ENGINE_VERSION = "0.1.1"


def _add_legacy_src_to_path() -> None:
    root = Path(__file__).resolve().parents[1]
    if root.name == "engine-python":
        root = root.parent
    legacy_src = root / "src"
    if legacy_src.exists():
        sys.path.insert(0, str(legacy_src))


def _module_available(name: str) -> bool:
    try:
        __import__(name)
    except Exception:
        return False
    return True


def _platform_name() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return system or sys.platform


def _native_acceleration() -> str:
    try:
        _add_legacy_src_to_path()
        from ubahin.native_bridge import native_status

        status = native_status()
        if status.get("available"):
            return str(status.get("backend") or "native")
    except Exception:
        pass
    return "fallback"


def _health_data() -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "python_available": True,
        "pymupdf_available": _module_available("fitz"),
        "pillow_available": _module_available("PIL"),
        "pypdf_available": _module_available("pypdf"),
        "native_acceleration": _native_acceleration(),
        "platform": _platform_name(),
    }


def _app_info() -> dict[str, Any]:
    return {
        "name": "Ubahin Engine",
        "engine_version": ENGINE_VERSION,
        "protocol": "json-lines",
        "platform": _platform_name(),
    }


def _self_check() -> dict[str, Any]:
    checks = _health_data()
    checks["ok"] = bool(checks["pymupdf_available"] and checks["pillow_available"] and checks["pypdf_available"])
    return checks


def _ok(request_id: str | None, data: dict[str, Any]) -> dict[str, Any]:
    return {"id": request_id, "ok": True, "data": data}


def _error(request_id: str | None, message: str, code: str = "ENGINE_ERROR") -> dict[str, Any]:
    return {
        "id": request_id,
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


def handle_request(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = payload.get("id")
    action = payload.get("action")
    if action == "health":
        return _ok(request_id, _health_data())
    if action == "app_info":
        return _ok(request_id, _app_info())
    if action == "self_check":
        data = _self_check()
        if data["ok"]:
            return _ok(request_id, data)
        return _error(request_id, "Komponen engine belum lengkap.")
    return _error(request_id, "Aksi engine tidak dikenal.", "UNKNOWN_ACTION")


def run_stdio() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("Request harus berupa object JSON.")
            response = handle_request(payload)
        except Exception as exc:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            response = _error(None, "Engine tidak dapat memproses request.")
        print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ubahin-engine")
    parser.add_argument("--stdio", action="store_true", help="Run JSON Lines protocol on stdin/stdout.")
    args = parser.parse_args(argv)
    if args.stdio:
        return run_stdio()
    print("Gunakan --stdio untuk menjalankan Ubahin Engine sebagai sidecar.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
