from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import fitz
import pytest
from pypdf import PdfReader

from ubahin.core import JobManager, JobStatus, ToolType
from ubahin.core.models import AppError
from ubahin.services import HistoryService
from ubahin.services import MergePdfOptions, MergePdfService


def _load_engine_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "engine-python" / "engine_main.py"
    spec = importlib.util.spec_from_file_location("ubahin_engine_main_merge", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_text_pdf(path: Path, labels: list[str]) -> Path:
    document = fitz.open()
    for label in labels:
        page = document.new_page(width=240, height=180)
        page.insert_text((36, 72), label)
    document.save(path)
    document.close()
    return path


def test_merge_pdf(sample_pdf: Path, second_pdf: Path, tmp_path: Path) -> None:
    result = MergePdfService().merge(
        [sample_pdf, second_pdf],
        MergePdfOptions(output_dir=tmp_path / "out", output_name="merged.pdf"),
    )
    assert len(result.output_paths) == 1
    assert len(PdfReader(str(result.output_paths[0])).pages) == 5
    assert result.total_input_files == 2
    assert result.processed_files == 2
    assert result.completed_files == 2
    assert result.output_paths[0].exists()
    assert result.output_paths[0].stat().st_size > 0


def test_merge_pdf_preserves_input_order(tmp_path: Path) -> None:
    first = _create_text_pdf(tmp_path / "first.pdf", ["FIRST-A", "FIRST-B"])
    second = _create_text_pdf(tmp_path / "second.pdf", ["SECOND-A"])

    result = MergePdfService().merge(
        [second, first],
        MergePdfOptions(output_dir=tmp_path / "out", output_name="ordered"),
    )

    output = result.output_paths[0]
    assert output.suffix == ".pdf"
    reader = PdfReader(str(output))
    text_by_page = [page.extract_text() for page in reader.pages]
    assert "SECOND-A" in text_by_page[0]
    assert "FIRST-A" in text_by_page[1]
    assert "FIRST-B" in text_by_page[2]


def test_merge_pdf_rejects_less_than_two_files(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(AppError, match="minimal dua"):
        MergePdfService().merge(
            [sample_pdf],
            MergePdfOptions(output_dir=tmp_path / "out", output_name="single.pdf"),
        )


def test_merge_pdf_rejects_invalid_pdf(sample_pdf: Path, tmp_path: Path) -> None:
    invalid = tmp_path / "not-a-pdf.pdf"
    invalid.write_text("bukan pdf", encoding="utf-8")

    with pytest.raises(AppError, match="PDF rusak"):
        MergePdfService().merge(
            [sample_pdf, invalid],
            MergePdfOptions(output_dir=tmp_path / "out", output_name="invalid.pdf"),
        )


def test_job_manager_merge_pdf_writes_history(sample_pdf: Path, second_pdf: Path, tmp_path: Path) -> None:
    history = HistoryService(tmp_path / "history.sqlite3")
    manager = JobManager(history_service=history)
    job = manager.create_job(
        ToolType.MERGE_PDF,
        [sample_pdf, second_pdf],
        tmp_path / "out",
        output_name="history.pdf",
    )

    manager.start_job(job.job_id)

    assert manager.wait(job.job_id, timeout=10)
    assert job.status == JobStatus.COMPLETED
    assert job.result is not None
    assert len(job.result.output_paths) == 1
    assert job.result.output_paths[0].exists()
    items = history.list_history(tool_type="merge_pdf")["items"]
    assert len(items) == 1
    assert items[0]["tool_type"] == "merge_pdf"
    assert items[0]["status"] == "completed"
    assert items[0]["output_count"] == 1


def test_engine_start_merge_pdf_emits_completion(sample_pdf: Path, second_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    engine_main = _load_engine_module()
    runtime = engine_main.EngineRuntime()
    messages: list[dict[str, object]] = []
    monkeypatch.setattr(runtime, "write_message", lambda message: messages.append(message))

    response = runtime.handle_request(
        {
            "id": "merge-1",
            "action": "start_merge_pdf",
            "payload": {
                "job_id": "merge-job-1",
                "files": [
                    {"file_id": "first", "path": str(sample_pdf)},
                    {"file_id": "second", "path": str(second_pdf)},
                ],
                "output_directory": str(tmp_path / "out"),
                "output_filename": "engine-merged.pdf",
                "open_output_after_finish": False,
                "performance_mode": "balanced",
            },
        }
    )

    assert response["id"] == "merge-1"
    assert response["ok"] is True
    assert runtime._manager.wait("merge-job-1", timeout=10)

    terminal_events = [
        message
        for message in messages
        if message.get("type") == "event" and message.get("event") in {"job_completed", "job_failed", "job_cancelled"}
    ]
    assert terminal_events
    assert terminal_events[-1]["event"] == "job_completed"
    payload = terminal_events[-1]["data"]
    assert isinstance(payload, dict)
    assert payload["tool_type"] == "merge_pdf"
    assert payload["total_outputs"] == 1
    assert payload["output_pdf_path"]
    assert Path(str(payload["output_pdf_path"])).exists()


def test_engine_start_merge_pdf_rejects_one_file(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    engine_main = _load_engine_module()
    runtime = engine_main.EngineRuntime()

    response = runtime.handle_request(
        {
            "id": "merge-one",
            "action": "start_merge_pdf",
            "payload": {
                "files": [{"file_id": "first", "path": str(sample_pdf)}],
                "output_directory": str(tmp_path / "out"),
                "output_filename": "one.pdf",
            },
        }
    )

    assert response["id"] == "merge-one"
    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_PAYLOAD"
