from __future__ import annotations

from pathlib import Path

from ubahin.core import JobManager, JobStatus
from ubahin.core.validation import validate_pdf_file
from ubahin.services import PdfToImageOptions, PdfToImageService


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
