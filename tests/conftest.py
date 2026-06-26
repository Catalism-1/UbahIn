from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PIL import Image


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    create_pdf(path, pages=3)
    return path


@pytest.fixture
def second_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "second.pdf"
    create_pdf(path, pages=2)
    return path


@pytest.fixture
def sample_images(tmp_path: Path) -> list[Path]:
    paths: list[Path] = []
    for index, suffix in enumerate(["jpg", "png", "webp"], start=1):
        path = tmp_path / f"image_{index}.{suffix}"
        image = Image.new("RGB", (120 + index * 10, 80 + index * 10), (30 * index, 90, 160))
        image.save(path)
        image.close()
        paths.append(path)
    return paths


def create_pdf(path: Path, pages: int = 2) -> None:
    document = fitz.open()
    for number in range(pages):
        page = document.new_page(width=240, height=180)
        page.insert_text((36, 72), f"Ubahin test page {number + 1}")
    document.save(path)
    document.close()
