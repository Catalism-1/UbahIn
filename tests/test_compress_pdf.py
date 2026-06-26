from __future__ import annotations

from pathlib import Path

from ubahin.services import CompressPdfOptions, CompressPdfService


def test_compress_pdf_safe_result(sample_pdf: Path, tmp_path: Path) -> None:
    result = CompressPdfService().compress(
        sample_pdf,
        CompressPdfOptions(output_dir=tmp_path / "out", preset="Ringan", keep_if_larger=True),
    )
    assert result.output_paths
    assert result.output_paths[0].exists()
