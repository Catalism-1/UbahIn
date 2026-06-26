from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from ubahin.services import ImageToPdfOptions, ImageToPdfService


def test_image_to_pdf(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    result = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(output_dir=output, output_name="images.pdf", page_size="A4"),
    )
    assert not result.errors
    assert len(result.output_paths) == 1
    reader = PdfReader(str(result.output_paths[0]))
    assert len(reader.pages) == len(sample_images)
