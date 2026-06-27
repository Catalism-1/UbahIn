from __future__ import annotations

import zipfile
from pathlib import Path

from ubahin.core import JobManager, JobStatus
from ubahin.core.validation import validate_pdf_file
from ubahin.services import HistoryService, PdfToImageOptions, PdfToImageService


def test_pdf_to_jpg_creates_one_jpg_per_page(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "out"
    result = PdfToImageService().convert_to_jpg(
        [sample_pdf],
        PdfToImageOptions(output_dir=output, dpi=120, jpg_quality=80),
    )
    assert not result.errors
    assert len(result.output_paths) == 3
    assert all(path.exists() and path.suffix.lower() == ".jpg" for path in result.output_paths)


def test_job_cancellation_before_start(sample_pdf: Path, tmp_path: Path) -> None:
    manager = JobManager()
    job = manager.create_job("pdf_to_jpg", [sample_pdf], tmp_path / "out")
    manager.cancel_job(job.job_id)
    manager.start_job(job.job_id)
    assert manager.wait(job.job_id, timeout=10)
    assert manager.get_job_status(job.job_id) == JobStatus.CANCELLED


def test_corrupt_pdf_validation(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a real pdf")
    try:
        validate_pdf_file(corrupt)
    except Exception as exc:
        assert "PDF" in str(exc)
    else:
        raise AssertionError("PDF rusak harus gagal divalidasi")


def test_password_pdf_validation(tmp_path: Path) -> None:
    protected = tmp_path / "protected.pdf"
    document = __import__("fitz").open()
    document.new_page()
    document.save(protected, encryption=__import__("fitz").PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
    document.close()
    try:
        validate_pdf_file(protected)
    except Exception as exc:
        assert "password" in str(exc).lower()
    else:
        raise AssertionError("PDF password harus gagal divalidasi")


def test_pdf_to_jpg_partial_batch_success(sample_pdf: Path, second_pdf: Path, tmp_path: Path) -> None:
    corrupt = tmp_path / "rusak.pdf"
    corrupt.write_bytes(b"not a real pdf")
    output = tmp_path / "out"
    history = HistoryService(tmp_path / "history.sqlite3")
    manager = JobManager(history_service=history)

    job = manager.create_job("pdf_to_jpg", [sample_pdf, corrupt, second_pdf], output, dpi=120, jpg_quality=80, create_zip=True)
    manager.start_job(job.job_id)

    assert manager.wait(job.job_id, timeout=20)
    final = manager.get_job(job.job_id)
    result = manager.get_job_result(job.job_id)
    assert result is not None
    assert final.status == JobStatus.COMPLETED_WITH_WARNINGS
    assert result.successful_files == 2
    assert result.failed_files == 1
    assert result.total_input_files == 3
    assert result.completed_files == 2
    assert any(fr.input_path.name == "rusak.pdf" and fr.status == "failed" for fr in result.file_results)

    jpgs = [path for path in result.output_paths if path.suffix.lower() == ".jpg"]
    zips = [path for path in result.output_paths if path.suffix.lower() == ".zip"]
    assert len(jpgs) == 5
    assert all(path.exists() for path in jpgs)
    assert len(zips) == 1 and zips[0].exists()
    with zipfile.ZipFile(zips[0]) as archive:
        members = archive.namelist()
    assert len(members) == 5
    assert all(member.endswith(".jpg") for member in members)
    assert "rusak" not in "\n".join(members)

    rows = history.list_recent()
    assert len(rows) == 1
    assert rows[0]["status"] == "completed_with_warnings"
    assert rows[0]["output_count"] == 6


def test_pdf_to_jpg_all_invalid_batch_fails(tmp_path: Path) -> None:
    bad_one = tmp_path / "rusak-1.pdf"
    bad_two = tmp_path / "rusak-2.pdf"
    bad_one.write_bytes(b"not a real pdf")
    bad_two.write_bytes(b"still not a real pdf")
    manager = JobManager(history_service=HistoryService(tmp_path / "history.sqlite3"))

    job = manager.create_job("pdf_to_jpg", [bad_one, bad_two], tmp_path / "out", dpi=120, jpg_quality=80, create_zip=True)
    manager.start_job(job.job_id)

    assert manager.wait(job.job_id, timeout=20)
    final = manager.get_job(job.job_id)
    result = manager.get_job_result(job.job_id)
    assert result is not None
    assert final.status == JobStatus.FAILED
    assert result.successful_files == 0
    assert result.failed_files == 2
    assert result.output_paths == []
    assert len(final.errors) == 2
    assert manager.get_job_history()[0]["status"] == "failed"
