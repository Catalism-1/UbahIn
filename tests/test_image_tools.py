from __future__ import annotations

from pathlib import Path

from PIL import Image

from ubahin.services import (
    ImageCompressOptions,
    ImageCompressService,
    ImageResizeOptions,
    ImageResizeService,
)


def test_image_resize_and_compress(sample_images: list[Path], tmp_path: Path) -> None:
    resized = ImageResizeService().resize(
        sample_images[:1],
        ImageResizeOptions(output_dir=tmp_path / "resized", percent=50),
    )
    with Image.open(sample_images[0]) as original, Image.open(resized.output_paths[0]) as output:
        assert output.width < original.width
        assert output.height < original.height

    compressed = ImageCompressService().compress(
        sample_images[:1],
        ImageCompressOptions(output_dir=tmp_path / "compressed", quality=70),
    )
    assert compressed.output_paths[0].exists()
