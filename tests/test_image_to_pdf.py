from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from ubahin.core import AppError
from ubahin.core.cancellation import CancellationToken
from ubahin.services import MAX_IMAGE_TO_PDF_FILES, ImageToPdfOptions, ImageToPdfService


def test_image_to_pdf_basic(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    result = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(output_dir=output, output_name="images.pdf", page_size="a4"),
    )
    assert not result.errors
    assert len(result.output_paths) == 1
    
    output_pdf = result.output_paths[0]
    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0
    
    # Verify open and page count
    reader = PdfReader(str(output_pdf))
    assert len(reader.pages) == len(sample_images)


def test_image_to_pdf_collision_suffix(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir(parents=True, exist_ok=True)
    
    # Create the first PDF
    first_pdf = output / "images.pdf"
    first_pdf.touch()
    
    result = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(output_dir=output, output_name="images.pdf", page_size="a4"),
    )
    assert not result.errors
    assert len(result.output_paths) == 1
    
    output_pdf = result.output_paths[0]
    assert output_pdf.name == "images_01.pdf"
    assert output_pdf.exists()


def test_image_to_pdf_non_writable(sample_images: list[Path], tmp_path: Path) -> None:
    # A non-writable path (using an existing file path as directory or using invalid directory path)
    output = tmp_path / "non_writable_file"
    output.touch()
    
    with pytest.raises(Exception):
        ImageToPdfService().convert(
            sample_images,
            ImageToPdfOptions(output_dir=output, output_name="images.pdf"),
        )


def test_image_to_pdf_cancellation(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    cancel_token = CancellationToken()
    cancel_token.cancel()
    
    with pytest.raises(InterruptedError):
        ImageToPdfService().convert(
            sample_images,
            ImageToPdfOptions(output_dir=output, output_name="images.pdf"),
            cancellation=cancel_token,
        )
        
    # Verify no partial file remains
    partial_files = list(output.glob("*.pdf")) + list(output.glob(".*.tmp*"))
    assert not any(p.exists() for p in partial_files)


def test_image_to_pdf_quality_presets(tmp_path: Path) -> None:
    output = tmp_path / "out"
    
    # Generate a rich 500x500 gradient image
    gradient_img_path = tmp_path / "gradient.jpg"
    img = Image.new("RGB", (500, 500))
    pixels = img.load()
    for y in range(500):
        for x in range(500):
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
    img.save(gradient_img_path, "JPEG")
    
    # Tinggi preset
    res_high = ImageToPdfService().convert(
        [gradient_img_path],
        ImageToPdfOptions(output_dir=output, output_name="high.pdf", image_quality_preset="high"),
    )
    assert not res_high.errors
    high_size = res_high.output_paths[0].stat().st_size
    
    # Seimbang preset
    res_balanced = ImageToPdfService().convert(
        [gradient_img_path],
        ImageToPdfOptions(output_dir=output, output_name="balanced.pdf", image_quality_preset="balanced"),
    )
    assert not res_balanced.errors
    balanced_size = res_balanced.output_paths[0].stat().st_size
    
    # Hemat preset
    res_compact = ImageToPdfService().convert(
        [gradient_img_path],
        ImageToPdfOptions(output_dir=output, output_name="compact.pdf", image_quality_preset="compact"),
    )
    assert not res_compact.errors
    compact_size = res_compact.output_paths[0].stat().st_size
    
    # Verify sizes decrease: Tinggi > Seimbang > Hemat
    assert high_size > balanced_size
    assert balanced_size > compact_size


def test_image_to_pdf_custom_qualities(tmp_path: Path) -> None:
    output = tmp_path / "out"
    
    # Generate a rich 500x500 gradient image
    gradient_img_path = tmp_path / "gradient.jpg"
    img = Image.new("RGB", (500, 500))
    pixels = img.load()
    for y in range(500):
        for x in range(500):
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
    img.save(gradient_img_path, "JPEG")
    
    # Custom 60
    res_60 = ImageToPdfService().convert(
        [gradient_img_path],
        ImageToPdfOptions(output_dir=output, output_name="q60.pdf", image_quality_preset="custom", jpeg_quality=60),
    )
    assert not res_60.errors
    size_60 = res_60.output_paths[0].stat().st_size

    # Custom 95
    res_95 = ImageToPdfService().convert(
        [gradient_img_path],
        ImageToPdfOptions(output_dir=output, output_name="q95.pdf", image_quality_preset="custom", jpeg_quality=95),
    )
    assert not res_95.errors
    size_95 = res_95.output_paths[0].stat().st_size
    
    assert size_95 > size_60


def test_image_to_pdf_clamping(sample_images: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    
    # Under limit (49 or 0) -> clamped to 50
    res_under = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(output_dir=output, output_name="clamped_under.pdf", image_quality_preset="custom", jpeg_quality=10),
    )
    assert not res_under.errors
    
    # Over limit (96 or 100) -> clamped to 95
    res_over = ImageToPdfService().convert(
        sample_images,
        ImageToPdfOptions(output_dir=output, output_name="clamped_over.pdf", image_quality_preset="custom", jpeg_quality=120),
    )
    assert not res_over.errors


def _make_images(directory: Path, count: int) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index in range(count):
        path = directory / f"batch_{index:04d}.png"
        Image.new("RGB", (12, 12), (index % 256, (index * 3) % 256, (index * 7) % 256)).save(path)
        paths.append(path)
    return paths


def test_image_to_pdf_accepts_100_images_with_100_pages(tmp_path: Path) -> None:
    images = _make_images(tmp_path / "images", MAX_IMAGE_TO_PDF_FILES)
    output = tmp_path / "out"

    result = ImageToPdfService().convert(
        images,
        ImageToPdfOptions(output_dir=output, output_name="hundred.pdf"),
    )

    assert not result.errors
    assert len(result.output_paths) == 1
    reader = PdfReader(str(result.output_paths[0]))
    assert len(reader.pages) == MAX_IMAGE_TO_PDF_FILES


def test_image_to_pdf_rejects_101_images(tmp_path: Path) -> None:
    # Count check happens before per-file validation, so paths need not exist.
    fake_paths = [tmp_path / f"fake_{index}.png" for index in range(MAX_IMAGE_TO_PDF_FILES + 1)]
    output = tmp_path / "out"

    with pytest.raises(AppError) as excinfo:
        ImageToPdfService().convert(
            fake_paths,
            ImageToPdfOptions(output_dir=output, output_name="rejected.pdf"),
        )
    assert f"Maksimal {MAX_IMAGE_TO_PDF_FILES}" in str(excinfo.value)
