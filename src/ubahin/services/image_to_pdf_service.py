from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_image_batch, validate_output_dir
from ubahin.utils import atomic_temp_path, finalize_atomic_write, get_logger, remove_temp_file, unique_file
from ubahin.utils.image_utils import normalize_rgb, open_image

logger = get_logger("ubahin.image_to_pdf")

# ---------- quality presets ------------------------------------------------

QUALITY_PRESETS: dict[str, dict[str, object]] = {
    "high": {"jpeg_quality": 95, "optimize_pdf_size": False},
    "balanced": {"jpeg_quality": 85, "optimize_pdf_size": True},
    "compact": {"jpeg_quality": 70, "optimize_pdf_size": True},
}

MIN_QUALITY = 50
MAX_QUALITY = 95


def _clamp_quality(value: int) -> int:
    return max(MIN_QUALITY, min(MAX_QUALITY, value))


def _resolve_quality(preset: str, explicit_quality: int | None) -> tuple[int, bool]:
    """Return (jpeg_quality, optimize_pdf_size) from preset or explicit value."""
    if preset == "custom" and explicit_quality is not None:
        return _clamp_quality(explicit_quality), True
    settings = QUALITY_PRESETS.get(preset, QUALITY_PRESETS["balanced"])
    quality = int(settings["jpeg_quality"])  # type: ignore[arg-type]
    optimize = bool(settings["optimize_pdf_size"])
    if explicit_quality is not None:
        quality = _clamp_quality(explicit_quality)
    return quality, optimize


# ---------- options --------------------------------------------------------

@dataclass(slots=True)
class ImageToPdfOptions:
    output_dir: Path
    output_name: str = "hasil_gambar.pdf"
    page_size: str = "original"
    orientation: str = "auto"
    margin: str = "normal"
    fit_mode: str = "contain"
    image_quality_preset: str = "balanced"
    jpeg_quality: int = 85
    optimize_pdf_size: bool = True


# ---------- service --------------------------------------------------------

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

        # Resolve quality
        jpeg_quality, optimize = _resolve_quality(
            options.image_quality_preset,
            options.jpeg_quality,
        )
        jpeg_quality = _clamp_quality(jpeg_quality)

        # Pre-validate file list
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

        # Ensure unique filename with .pdf extension
        output_name = options.output_name
        if not output_name.lower().endswith(".pdf"):
            output_name = f"{output_name}.pdf"
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

            # ---- write PDF via atomic temp file ----
            first, rest = pages[0], pages[1:]
            temp_path = atomic_temp_path(output_path)
            try:
                first.save(
                    temp_path,
                    "PDF",
                    save_all=True,
                    append_images=rest,
                    resolution=100,
                    quality=jpeg_quality,
                    optimize=optimize,
                )
                finalize_atomic_write(temp_path, output_path)
            except Exception:
                remove_temp_file(temp_path)
                raise

            # ---- validate output PDF ----
            validation_error = self._validate_output(output_path, len(valid_files))
            if validation_error:
                # PDF is invalid – remove it and report failure
                logger.error("Output PDF gagal validasi: %s", validation_error)
                remove_temp_file(output_path)
                return ServiceResult(
                    output_paths=[],
                    file_results=file_results,
                    errors=[validation_error] + errors,
                    message="PDF belum berhasil dibuat. Silakan cek folder hasil atau buka log.",
                    total_input_files=len(image_files),
                    processed_files=len(image_files),
                    completed_files=0,
                )

            output_size = output_path.stat().st_size
            for fr in file_results:
                if fr.status == "completed":
                    fr.output_paths = [output_path]
                    fr.output_size = output_size

            return ServiceResult(
                output_paths=[output_path],
                file_results=file_results,
                warnings=errors if errors else [],
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

    @staticmethod
    def _validate_output(output_path: Path, expected_pages: int) -> str | None:
        """Validate that the output PDF exists, is non-empty, and has the correct page count.

        Returns None if valid, or an error message string if invalid.
        """
        if not output_path.exists():
            return f"File PDF tidak ditemukan di {output_path}"

        size = output_path.stat().st_size
        if size == 0:
            return "File PDF kosong (0 byte)."

        try:
            from pypdf import PdfReader
            reader = PdfReader(str(output_path))
            actual_pages = len(reader.pages)
            if actual_pages != expected_pages:
                return (
                    f"Jumlah halaman PDF ({actual_pages}) tidak sesuai "
                    f"jumlah gambar valid ({expected_pages})."
                )
        except Exception as exc:
            return f"PDF tidak dapat dibuka ulang untuk validasi: {exc}"

        return None

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
