from __future__ import annotations

from pathlib import Path

from ubahin.core.validation import parse_page_ranges, validate_image_file, validate_pdf_batch


def test_page_range_parser() -> None:
    assert parse_page_ranges("1-3, 4, 5-6", 6) == [(1, 3), (4, 4), (5, 6)]


def test_pdf_batch_limit(sample_pdf: Path) -> None:
    try:
        validate_pdf_batch([sample_pdf] * 51, max_files=50)
    except Exception as exc:
        assert "Maksimal" in str(exc)
    else:
        raise AssertionError("Batch lebih dari 50 harus gagal")


def test_image_validation(sample_images: list[Path]) -> None:
    validate_image_file(sample_images[0])
