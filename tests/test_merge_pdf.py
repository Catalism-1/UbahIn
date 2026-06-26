from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from ubahin.services import MergePdfOptions, MergePdfService


def test_merge_pdf(sample_pdf: Path, second_pdf: Path, tmp_path: Path) -> None:
    result = MergePdfService().merge(
        [sample_pdf, second_pdf],
        MergePdfOptions(output_dir=tmp_path / "out", output_name="merged.pdf"),
    )
    assert len(result.output_paths) == 1
    assert len(PdfReader(str(result.output_paths[0])).pages) == 5
