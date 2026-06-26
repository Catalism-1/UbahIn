from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import fitz
from PIL import Image

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_output_dir, validate_pdf_batch
from ubahin.utils import sanitize_filename, unique_directory, unique_file


ProgressCallback = Callable[[ProgressInfo], None]


@dataclass(slots=True)
class PdfToImageOptions:
    output_dir: Path
    dpi: int = 200
    jpg_quality: int = 90
    preset: str = "Tinggi"
    white_background: bool = True
    optimize_size: bool = True
    max_files: int = 50


class PdfToImageService:
    def convert_to_jpg(
        self,
        pdf_files: list[Path],
        options: PdfToImageOptions,
        cancellation: CancellationToken | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        options.output_dir = Path(options.output_dir).expanduser().resolve()
        validate_output_dir(options.output_dir)
        total_pages = validate_pdf_batch(pdf_files, options.max_files)
        completed_pages = 0
        result = ServiceResult(message="Konversi PDF ke JPG selesai.")

        for file_index, pdf_path in enumerate(pdf_files, start=1):
            cancellation.raise_if_cancelled()
            file_result = FileResult(input_path=pdf_path, input_size=pdf_path.stat().st_size)
            result.file_results.append(file_result)
            safe_stem = sanitize_filename(pdf_path.stem, "dokumen")
            try:
                output_folder = unique_directory(options.output_dir, safe_stem)
                with fitz.open(pdf_path) as document:
                    if document.needs_pass:
                        raise ValueError("PDF terkunci password.")
                    for page_index in range(document.page_count):
                        cancellation.raise_if_cancelled()
                        page = document.load_page(page_index)
                        pixmap = page.get_pixmap(dpi=options.dpi, alpha=options.white_background)
                        if options.white_background:
                            rgba = Image.frombytes("RGBA", (pixmap.width, pixmap.height), pixmap.samples)
                            image = Image.new("RGB", rgba.size, "white")
                            image.paste(rgba, mask=rgba.getchannel("A"))
                            rgba.close()
                        else:
                            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                        output_path = unique_file(output_folder, f"{safe_stem}_page_{page_index + 1:03d}.jpg")
                        save_args: dict[str, object] = {"quality": options.jpg_quality}
                        if options.optimize_size:
                            save_args.update({"optimize": True, "progressive": True})
                        if options.jpg_quality >= 90:
                            save_args["subsampling"] = 0
                        image.save(output_path, "JPEG", **save_args)
                        image.close()
                        file_result.output_paths.append(output_path)
                        result.output_paths.append(output_path)
                        completed_pages += 1
                        if on_progress:
                            on_progress(
                                ProgressInfo(
                                    percentage=(completed_pages / max(total_pages, 1)) * 100,
                                    current_file=pdf_path.name,
                                    current_page=page_index + 1,
                                    total_pages=document.page_count,
                                    current_item=file_index,
                                    total_items=len(pdf_files),
                                    message=f"Memproses halaman {page_index + 1}/{document.page_count}",
                                )
                            )
                file_result.output_size = sum(path.stat().st_size for path in file_result.output_paths)
            except Exception as exc:
                file_result.status = "failed"
                file_result.error = str(exc)
                result.errors.append(f"{pdf_path.name}: {exc}")
                continue
        return result
