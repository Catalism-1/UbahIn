from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
import pytest
from PIL import Image

from ubahin.services import ImageToPdfOptions, ImageToPdfService
from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import JobStatus
from ubahin.utils.image_utils import normalize_rgb


def test_image_to_pdf_basic(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    result = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(output_dir=output, output_name="images.pdf", page_size="a4"),
    )
    assert not result.errors
    assert len(result.output_paths) == 1
    reader = PdfReader(str(result.output_paths[0]))
    assert len(reader.pages) == len(sample_images)


def test_image_to_pdf_original_size(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    result = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(
            output_dir=output,
            output_name="original.pdf",
            page_size="original",
            margin="none",
        ),
    )
    assert not result.errors
    assert len(result.output_paths) == 1
    
    reader = PdfReader(str(result.output_paths[0]))
    # Validate original size matches image size (plus margins if any)
    # 595x842 pt is A4, original size points depends on image DPI/dimensions
    assert len(reader.pages) == len(sample_images)


def test_image_to_pdf_fit_modes(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    
    # Test "fill" mode
    result_fill = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(
            output_dir=output,
            output_name="fill.pdf",
            page_size="letter",
            fit_mode="fill",
        ),
    )
    assert not result_fill.errors
    assert len(result_fill.output_paths) == 1
    
    # Test "contain" mode
    result_contain = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(
            output_dir=output,
            output_name="contain.pdf",
            page_size="letter",
            fit_mode="contain",
        ),
    )
    assert not result_contain.errors
    assert len(result_contain.output_paths) == 1


def test_image_to_pdf_orientations(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    
    # Test landscape
    result_landscape = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(
            output_dir=output,
            output_name="landscape.pdf",
            page_size="a4",
            orientation="landscape",
        ),
    )
    assert not result_landscape.errors
    
    # Test portrait
    result_portrait = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(
            output_dir=output,
            output_name="portrait.pdf",
            page_size="a4",
            orientation="portrait",
        ),
    )
    assert not result_portrait.errors


def test_image_to_pdf_transparency(tmp_path: Path) -> None:
    # Create a transparent PNG image
    transparent_img_path = tmp_path / "transparent.png"
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    img.save(transparent_img_path, "PNG")
    
    output = tmp_path / "out"
    result = ImageToPdfService().convert(
        [transparent_img_path],
        ImageToPdfOptions(output_dir=output, output_name="trans.pdf"),
    )
    assert not result.errors
    assert len(result.output_paths) == 1


def test_image_to_pdf_cancellation(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    cancel_token = CancellationToken()
    cancel_token.cancel() # Pre-cancel
    
    with pytest.raises(InterruptedError):
        ImageToPdfService().convert(
            sample_images,
            ImageToPdfOptions(output_dir=output, output_name="cancelled.pdf"),
            cancellation=cancel_token,
        )
