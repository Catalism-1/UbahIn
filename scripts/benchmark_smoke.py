from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ubahin.services import ImageCompressOptions, ImageCompressService, PdfToImageOptions, PdfToImageService
from ubahin.utils.benchmark_utils import benchmark


def create_pdf(path: Path, pages: int = 10) -> None:
    document = fitz.open()
    for index in range(pages):
        page = document.new_page(width=240, height=180)
        page.insert_text((36, 72), f"Benchmark page {index + 1}")
    document.save(path)
    document.close()


def main() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf = root / "bench.pdf"
        create_pdf(pdf)
        images = []
        for index in range(5):
            image_path = root / f"image_{index}.jpg"
            image = Image.new("RGB", (800, 600), (40 + index, 80, 120))
            image.save(image_path, quality=95)
            image.close()
            images.append(image_path)

        with benchmark("pdf_10_pages") as pdf_result:
            PdfToImageService().convert_to_jpg([pdf], PdfToImageOptions(output_dir=root / "pdf_out", dpi=120, jpg_quality=80))
        with benchmark("image_batch") as image_result:
            ImageCompressService().compress(images, ImageCompressOptions(output_dir=root / "img_out", quality=80))
        for item in pdf_result + image_result:
            print(f"{item.name}: {item.duration_seconds:.3f}s rss={item.memory_rss_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
