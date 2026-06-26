from __future__ import annotations

from pathlib import Path

from ubahin.desktop.pages.pdf_to_jpg_page import ConversionRequest
from ubahin.models import QualityPreset


def test_conversion_request_is_plain_worker_payload(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    request = ConversionRequest(
        input_paths=[source],
        output_dir=tmp_path / "out",
        quality_preset=QualityPreset.HIGH,
        dpi=200,
        jpeg_quality=90,
        create_zip=True,
        open_after_finish=False,
        optimize_file_size=True,
    )

    assert request.input_paths == [source]
    assert request.quality_preset == QualityPreset.HIGH
    assert request.dpi == 200
    assert request.jpeg_quality == 90
    assert request.create_zip is True
