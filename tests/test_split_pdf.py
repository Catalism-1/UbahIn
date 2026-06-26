from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from ubahin.services import SplitPdfOptions, SplitPdfService


def test_split_pdf_ranges(sample_pdf: Path, tmp_path: Path) -> None:
    result = SplitPdfService().split(
        sample_pdf,
        SplitPdfOptions(output_dir=tmp_path / "out", mode="ranges", ranges="1-2,3"),
    )
    assert len(result.output_paths) == 2
    assert len(PdfReader(str(result.output_paths[0])).pages) == 2
    assert len(PdfReader(str(result.output_paths[1])).pages) == 1
