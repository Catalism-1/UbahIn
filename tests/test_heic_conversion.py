from __future__ import annotations

import os
from pathlib import Path
import pytest
from PIL import Image

from ubahin.services import HeicToImageOptions, HeicConversionService
from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import JobStatus


@pytest.fixture
def sample_heic_files(tmp_path: Path) -> list[Path]:
    import pillow_heif
    pillow_heif.register_heif_opener()
    
    heic_paths = []
    # Create 2 dummy HEIC files
    for i in range(2):
        img_path = tmp_path / f"test_{i}.heic"
        img = Image.new("RGB", (150, 100), color="blue" if i == 0 else "red")
        img.save(img_path, "HEIF")
        heic_paths.append(img_path)
    return heic_paths


def test_heic_to_jpg_basic(sample_heic_files: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    result = HeicConversionService().convert(
        sample_heic_files,
        HeicToImageOptions(output_dir=output, output_format="jpg", jpeg_quality_preset="balanced"),
    )
    assert not result.errors
    assert len(result.output_paths) == 2
    
    for path in result.output_paths:
        assert path.exists()
        assert path.suffix.lower() == ".jpg"
        assert path.stat().st_size > 0
        
        # Verify it can be opened as image
        with Image.open(path) as img:
            assert img.format == "JPEG"
            assert img.width == 150
            assert img.height == 100


def test_heic_to_png_basic(sample_heic_files: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    result = HeicConversionService().convert(
        sample_heic_files,
        HeicToImageOptions(output_dir=output, output_format="png", png_compression_level=6),
    )
    assert not result.errors
    assert len(result.output_paths) == 2
    
    for path in result.output_paths:
        assert path.exists()
        assert path.suffix.lower() == ".png"
        assert path.stat().st_size > 0
        
        with Image.open(path) as img:
            assert img.format == "PNG"


def test_heic_to_jpg_presets(sample_heic_files: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    # Convert with High preset
    res_high = HeicConversionService().convert(
        [sample_heic_files[0]],
        HeicToImageOptions(output_dir=output, output_format="jpg", jpeg_quality_preset="high"),
    )
    assert not res_high.errors
    high_size = res_high.output_paths[0].stat().st_size
    
    # Convert with Balanced preset
    res_balanced = HeicConversionService().convert(
        [sample_heic_files[0]],
        HeicToImageOptions(output_dir=output, output_format="jpg", jpeg_quality_preset="balanced"),
    )
    assert not res_balanced.errors
    balanced_size = res_balanced.output_paths[0].stat().st_size

    # Convert with Compact preset
    res_compact = HeicConversionService().convert(
        [sample_heic_files[0]],
        HeicToImageOptions(output_dir=output, output_format="jpg", jpeg_quality_preset="compact"),
    )
    assert not res_compact.errors
    compact_size = res_compact.output_paths[0].stat().st_size
    
    assert high_size >= balanced_size
    assert balanced_size >= compact_size


def test_heic_collision_suffix(sample_heic_files: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir(parents=True, exist_ok=True)
    
    # Touch target file first to force suffix
    target_jpg = output / "test_0.jpg"
    target_jpg.touch()
    
    result = HeicConversionService().convert(
        [sample_heic_files[0]],
        HeicToImageOptions(output_dir=output, output_format="jpg"),
    )
    assert not result.errors
    assert len(result.output_paths) == 1
    
    output_file = result.output_paths[0]
    assert output_file.name == "test_0_01.jpg"
    assert output_file.exists()


def test_heic_cancellation(sample_heic_files: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "out"
    cancel_token = CancellationToken()
    cancel_token.cancel()
    
    with pytest.raises(InterruptedError):
        HeicConversionService().convert(
            sample_heic_files,
            HeicToImageOptions(output_dir=output, output_format="jpg"),
            cancellation=cancel_token,
        )
        
    # Verify no partial files remain
    partial_files = list(output.glob("*.jpg")) + list(output.glob(".*.tmp*"))
    assert not any(p.exists() for p in partial_files)
