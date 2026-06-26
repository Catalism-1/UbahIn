from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_image_batch, validate_output_dir
from ubahin.utils import unique_file
from ubahin.utils.image_utils import normalize_rgb, open_image


@dataclass(slots=True)
class ImageToPdfOptions:
    output_dir: Path
    output_name: str = "hasil_gambar.pdf"
    page_size: str = "Original"
    orientation: str = "Otomatis"
    margin: str = "Normal"


class ImageToPdfService:
    PAGE_SIZES = {
        "A4": (595, 842),
        "Letter": (612, 792),
    }
    MARGINS = {"Tanpa margin": 0, "Kecil": 18, "Normal": 36}

    def convert(
        self,
        image_files: list[Path],
        options: ImageToPdfOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        options.output_dir = Path(options.output_dir).expanduser().resolve()
        validate_output_dir(options.output_dir)
        validate_image_batch(image_files)

        pages: list[Image.Image] = []
        output_path = unique_file(options.output_dir, options.output_name)
        try:
            for index, image_path in enumerate(image_files, start=1):
                cancellation.raise_if_cancelled()
                image = normalize_rgb(open_image(image_path))
                prepared = self._prepare_page(image, options)
                pages.append(prepared)
                if on_progress:
                    on_progress(
                        ProgressInfo(
                            percentage=(index / len(image_files)) * 100,
                            current_file=image_path.name,
                            current_item=index,
                            total_items=len(image_files),
                            message="Menambahkan gambar ke PDF",
                        )
                    )
            first, rest = pages[0], pages[1:]
            first.save(output_path, "PDF", save_all=True, append_images=rest, resolution=100)
            return ServiceResult(
                output_paths=[output_path],
                file_results=[FileResult(input_path=image_files[0], output_paths=[output_path], output_size=output_path.stat().st_size)],
                message="Gambar berhasil dibuat menjadi PDF.",
            )
        finally:
            for page in pages:
                page.close()

    def _prepare_page(self, image: Image.Image, options: ImageToPdfOptions) -> Image.Image:
        if options.page_size == "Original":
            return image.copy()
        width, height = self.PAGE_SIZES.get(options.page_size, self.PAGE_SIZES["A4"])
        if options.orientation == "Landscape" or (options.orientation == "Otomatis" and image.width > image.height):
            width, height = max(width, height), min(width, height)
        else:
            width, height = min(width, height), max(width, height)
        margin = self.MARGINS.get(options.margin, 36)
        canvas = Image.new("RGB", (width, height), "white")
        max_width = max(width - margin * 2, 1)
        max_height = max(height - margin * 2, 1)
        fitted = image.copy()
        fitted.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        left = (width - fitted.width) // 2
        top = (height - fitted.height) // 2
        canvas.paste(fitted, (left, top))
        fitted.close()
        return canvas
