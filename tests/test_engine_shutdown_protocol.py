from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_engine_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "engine-python" / "engine_main.py"
    spec = importlib.util.spec_from_file_location("ubahin_engine_main", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_engine_shutdown_returns_valid_json_response(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    engine_main = _load_engine_module()
    runtime = engine_main.EngineRuntime()

    response = runtime.handle_request(
        {
            "id": "shutdown-test",
            "action": "shutdown",
            "payload": {"cancel_active": True, "timeout_seconds": 0.1},
        }
    )

    assert response["type"] == "response"
    assert response["id"] == "shutdown-test"
    assert response["ok"] is True
    assert response["data"]["cleanup_completed"] is True
    assert response["data"]["active_jobs_remaining"] == []
