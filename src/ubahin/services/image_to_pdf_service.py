from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_image_batch, validate_output_dir
from ubahin.utils import atomic_temp_path, finalize_atomic_write, remove_temp_file, unique_file
from ubahin.utils.image_utils import normalize_rgb, open_image


@dataclass(slots=True)
class ImageToPdfOptions:
    output_dir: Path
    output_name: str = "hasil_gambar.pdf"
    page_size: str = "original"
    orientation: str = "auto"
    margin: str = "normal"
    fit_mode: str = "contain"


class ImageToPdfService:
    PAGE_SIZES = {
        "a4": (595, 842),
        "letter": (612, 792),
    }
    MARGINS = {
        "none": 0,
        "small": 18,
        "normal": 36,
    }

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

        # Pre-validate file list, skip corrupted images but continue with valid ones
        valid_files: list[Path] = []
        file_results: list[FileResult] = []
        errors: list[str] = []

        for path in image_files:
            try:
                if not path.exists():
                    raise FileNotFoundError("File tidak ditemukan.")
                with Image.open(path) as img:
                    _ = img.format
                valid_files.append(path)
                file_results.append(
                    FileResult(
                        input_path=path,
                        status="completed",
                        input_size=path.stat().st_size,
                    )
                )
            except Exception as exc:
                err_msg = f"{path.name}: {exc}"
                errors.append(err_msg)
                file_results.append(
                    FileResult(
                        input_path=path,
                        status="failed",
                        error=str(exc),
                        input_size=path.stat().st_size if path.exists() else 0,
                    )
                )

        if not valid_files:
            return ServiceResult(
                output_paths=[],
                file_results=file_results,
                errors=errors or ["Semua gambar tidak valid."],
                message="Gagal membuat PDF karena tidak ada gambar valid.",
                total_input_files=len(image_files),
                processed_files=len(image_files),
                completed_files=0,
            )

        # Ensure unique filename
        output_name = options.output_name if options.output_name.lower().endswith(".pdf") else f"{options.output_name}.pdf"
        output_path = unique_file(options.output_dir, output_name)

        cancellation.raise_if_cancelled()
        pages: list[Image.Image] = []
        try:
            for idx, image_path in enumerate(valid_files, start=1):
                cancellation.raise_if_cancelled()
                img = normalize_rgb(open_image(image_path))
                try:
                    prepared = self._prepare_page(img, options)
                    pages.append(prepared)
                finally:
                    img.close()

                if on_progress:
                    on_progress(
                        ProgressInfo(
                            percentage=(idx / len(valid_files)) * 100,
                            current_file=image_path.name,
                            current_item=idx,
                            total_items=len(valid_files),
                            message=f"Menambahkan gambar {idx} dari {len(valid_files)} ke PDF",
                        )
                    )

            cancellation.raise_if_cancelled()
            first, rest = pages[0], pages[1:]
            temp_path = atomic_temp_path(output_path)
            try:
                first.save(
                    temp_path,
                    "PDF",
                    save_all=True,
                    append_images=rest,
                    resolution=100,
                )
                finalize_atomic_write(temp_path, output_path)
            except Exception:
                remove_temp_file(temp_path)
                raise

            output_size = output_path.stat().st_size if output_path.exists() else 0
            for fr in file_results:
                if fr.status == "completed":
                    fr.output_paths = [output_path]
                    fr.output_size = output_size

            return ServiceResult(
                output_paths=[output_path],
                file_results=file_results,
                warnings=errors,
                message="Gambar berhasil dibuat menjadi PDF.",
                total_input_files=len(image_files),
                processed_files=len(image_files),
                completed_files=len(valid_files),
            )
        finally:
            for page in pages:
                try:
                    page.close()
                except Exception:
                    pass

    def _prepare_page(self, image: Image.Image, options: ImageToPdfOptions) -> Image.Image:
        margin_val = self.MARGINS.get(options.margin.lower(), 36)

        if options.page_size.lower() == "original":
            width = image.width + margin_val * 2
            height = image.height + margin_val * 2
            canvas = Image.new("RGB", (width, height), "white")
            canvas.paste(image, (margin_val, margin_val))
            return canvas

        width, height = self.PAGE_SIZES.get(options.page_size.lower(), self.PAGE_SIZES["a4"])
        orientation = options.orientation.lower()

        if orientation == "landscape" or (orientation == "auto" and image.width > image.height):
            width, height = max(width, height), min(width, height)
        else:
            width, height = min(width, height), max(width, height)

        max_width = max(width - margin_val * 2, 1)
        max_height = max(height - margin_val * 2, 1)
        canvas = Image.new("RGB", (width, height), "white")

        if options.fit_mode.lower() == "fill":
            img_ratio = image.width / image.height
            target_ratio = max_width / max_height
            if img_ratio > target_ratio:
                new_h = max_height
                new_w = int(round(max_height * img_ratio))
                resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left_crop = (new_w - max_width) // 2
                fitted = resized.crop((left_crop, 0, left_crop + max_width, max_height))
                resized.close()
            else:
                new_w = max_width
                new_h = int(round(max_width / img_ratio))
                resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                top_crop = (new_h - max_height) // 2
                fitted = resized.crop((0, top_crop, max_width, top_crop + max_height))
                resized.close()
        else:
            # Default to "contain"
            fitted = image.copy()
            fitted.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        left = (width - fitted.width) // 2
        top = (height - fitted.height) // 2
        canvas.paste(fitted, (left, top))
        fitted.close()
        return canvas
