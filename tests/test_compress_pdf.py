from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from ubahin.core import FileResult, JobStatus, ServiceResult, ToolType
from ubahin.services import CompressPdfOptions, CompressPdfService


def _load_engine_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "engine-python" / "engine_main.py"
    spec = importlib.util.spec_from_file_location("ubahin_engine_main_compress", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compress_pdf_safe_result(sample_pdf: Path, tmp_path: Path) -> None:
    result = CompressPdfService().compress(
        sample_pdf,
        CompressPdfOptions(output_dir=tmp_path / "out", preset="Ringan", keep_if_larger=True),
    )
    assert result.output_paths
    assert result.output_paths[0].exists()


def test_engine_compress_pdf_noop_emits_completed_with_warnings(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    engine_main = _load_engine_module()
    runtime = engine_main.EngineRuntime()
    messages: list[dict[str, object]] = []
    monkeypatch.setattr(runtime, "write_message", lambda message: messages.append(message))

    manager = runtime._manager
    job = manager.create_job(
        ToolType.COMPRESS_PDF,
        [sample_pdf],
        tmp_path / "out",
        keep_if_larger=False,
    )

    def fake_execute(_job):
        return ServiceResult(
            file_results=[
                FileResult(
                    input_path=sample_pdf,
                    status="skipped",
                    input_size=sample_pdf.stat().st_size,
                    output_size=sample_pdf.stat().st_size + 1,
                )
            ],
            message="Kompresi tidak menghemat ukuran. File hasil tidak disimpan.",
            total_input_files=1,
            processed_files=1,
        )

    monkeypatch.setattr(manager, "_execute", fake_execute)

    manager.start_job(job.job_id)

    assert manager.wait(job.job_id, timeout=10)
    assert job.status == JobStatus.COMPLETED_WITH_WARNINGS
    assert job.warnings == ["Kompresi tidak menghemat ukuran. File hasil tidak disimpan."]

    terminal_events = [
        message
        for message in messages
        if message.get("type") == "event" and message.get("event") in {"job_completed", "job_failed", "job_cancelled"}
    ]
    assert terminal_events
    assert terminal_events[-1]["event"] == "job_completed"
    payload = terminal_events[-1]["data"]
    assert isinstance(payload, dict)
    assert payload["status"] == "completed_with_warnings"
    assert payload["skipped_files"] == 1
    assert payload["total_outputs"] == 0
