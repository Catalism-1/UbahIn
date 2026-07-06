from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType


def _load_engine_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "engine-python" / "engine_main.py"
    spec = importlib.util.spec_from_file_location("ubahin_engine_main_health", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_health_request_returns_engine_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    engine_main = _load_engine_module()
    runtime = engine_main.EngineRuntime()

    response = runtime.handle_request({"id": "health-1", "action": "health", "payload": {}})

    assert response["id"] == "health-1"
    assert response["ok"] is True
    assert response["data"]["engine_version"]
    assert response["data"]["python_available"] is True
    assert "pymupdf_available" in response["data"]
    assert "pillow_available" in response["data"]
    assert "pypdf_available" in response["data"]
    assert response["data"]["platform"]


def test_stdio_unexpected_error_preserves_request_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    engine_main = _load_engine_module()

    def raise_from_handle(self, payload):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(engine_main.EngineRuntime, "handle_request", raise_from_handle)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"id":"req-error","action":"health","payload":{}}\n'))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    assert engine_main.run_stdio() == 0

    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == 1
    response = json.loads(lines[0])
    assert response["id"] == "req-error"
    assert response["ok"] is False
    assert response["error"]["code"] == "ENGINE_ERROR"
