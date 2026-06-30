from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps
import pillow_heif

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_output_dir, validate_existing_files
from ubahin.utils import finalize_atomic_write, get_logger, remove_temp_file, unique_file

logger = get_logger("ubahin.heic_conversion")

# Register pillow heif opener globally
try:
    pillow_heif.register_heif_opener()
except Exception as e:
    logger.error("Gagal mendaftarkan pillow-heif opener: %s", e)


@dataclass(slots=True)
class HeicToImageOptions:
    output_dir: Path
    output_format: str = "jpg"  # "jpg" atau "png"
    jpeg_quality_preset: str = "balanced"
    jpeg_quality: int = 85
    png_compression_level: int = 6
    preserve_metadata: bool = False


class HeicConversionService:
    def convert(
        self,
        heic_files: list[Path],
        options: HeicToImageOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        options.output_dir = Path(options.output_dir).expanduser().resolve()
        validate_output_dir(options.output_dir)

        # Pre-validate file extensions and existence
        SUPPORTED_HEIC_SUFFIXES = {".heic", ".heif"}
        validate_existing_files(heic_files, SUPPORTED_HEIC_SUFFIXES)

        result = ServiceResult(message="Foto HEIC/HEIF berhasil dikonversi.")
        format_target = options.output_format.lower()
        suffix = ".jpg" if format_target == "jpg" else ".png"
        save_format = "JPEG" if format_target == "jpg" else "PNG"

        # Resolve quality preset for JPEG
        if format_target == "jpg":
            if options.jpeg_quality_preset == "high":
                quality = 95
            elif options.jpeg_quality_preset == "balanced":
                quality = 85
            elif options.jpeg_quality_preset == "compact":
                quality = 70
            else:  # custom
                quality = max(50, min(95, options.jpeg_quality))
        else:
            quality = 85  # unused for PNG

        for index, file_path in enumerate(heic_files, start=1):
            cancellation.raise_if_cancelled()
            file_result = FileResult(input_path=file_path, input_size=file_path.stat().st_size)
            
            # Setup temp folder inside output dir
            temp_dir = options.output_dir / ".ubahin-temp"
            output_path = unique_file(options.output_dir, f"{file_path.stem}{suffix}")
            temp_path = temp_dir / f"{output_path.name}.tmp{suffix}"

            try:
                # 1. Buat file temporary.
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                with Image.open(file_path) as img:
                    # Fix EXIF orientation
                    transposed = ImageOps.exif_transpose(img)
                    
                    # Convert to appropriate format color space
                    if save_format == "JPEG":
                        # JPEG doesn't support alpha, normalize transparency to white
                        if transposed.mode in ("RGBA", "LA") or (transposed.mode == "P" and "transparency" in transposed.info):
                            rgba_img = transposed.convert("RGBA")
                            canvas = Image.new("RGB", rgba_img.size, "white")
                            canvas.paste(rgba_img, mask=rgba_img.getchannel("A"))
                            processed_img = canvas
                            transposed.close()
                        else:
                            processed_img = transposed.convert("RGB")
                            if processed_img is not transposed:
                                transposed.close()
                    else:
                        processed_img = transposed

                    # Determine saving arguments
                    save_args = {}
                    if save_format == "JPEG":
                        save_args["quality"] = quality
                    else:  # PNG
                        save_args["compress_level"] = max(0, min(9, options.png_compression_level))

                    if options.preserve_metadata:
                        try:
                            # Preserve EXIF data from original image minus orientation tag
                            exif_data = transposed.getexif() if hasattr(transposed, "getexif") else img.getexif()
                            if exif_data:
                                save_args["exif"] = exif_data
                        except Exception as exif_err:
                            logger.warning("Gagal mempreservasi metadata EXIF untuk %s: %s", file_path.name, exif_err)

                    processed_img.save(temp_path, save_format, **save_args)
                    processed_img.close()

                # 2. Verifikasi file temporary.
                validation_error = self._validate_file_integrity(temp_path)
                if validation_error:
                    raise ValueError(f"Hasil temporary tidak valid: {validation_error}")

                logger.info("TEMP_OUTPUT_CREATED path=%s", temp_path)

                # 3. Rename atomic ke file final.
                finalize_atomic_write(temp_path, output_path)
                logger.info("FINAL_OUTPUT_RENAMED path=%s", output_path)

                # Cleanup .ubahin-temp directory if empty
                try:
                    if temp_dir.exists() and not any(temp_dir.iterdir()):
                        temp_dir.rmdir()
                except Exception:
                    pass

                # 4. Verifikasi file final.
                validation_error = self._validate_file_integrity(output_path)
                if validation_error:
                    raise ValueError(f"Hasil final tidak valid: {validation_error}")

                output_size = output_path.stat().st_size
                logger.info("FINAL_OUTPUT_VERIFIED size=%d", output_size)

                file_result.output_paths = [output_path]
                file_result.output_size = output_size
                result.output_paths.append(output_path)

            except Exception as exc:
                import traceback
                logger.error("Gagal mengonversi file %s: %s\n%s", file_path.name, exc, traceback.format_exc())
                remove_temp_file(temp_path)
                remove_temp_file(output_path)
                # Cleanup .ubahin-temp directory if empty
                try:
                    if temp_dir.exists() and not any(temp_dir.iterdir()):
                        temp_dir.rmdir()
                except Exception:
                    pass
                
                file_result.status = "failed"
                file_result.error = str(exc)
                result.errors.append(f"{file_path.name}: {exc}")

            result.file_results.append(file_result)

            if on_progress:
                on_progress(
                    ProgressInfo(
                        percentage=(index / len(heic_files)) * 100,
                        current_file=file_path.name,
                        current_item=index,
                        total_items=len(heic_files),
                        message=f"Mengonversi foto {index} dari {len(heic_files)}",
                    )
                )

        result.total_input_files = len(heic_files)
        result.processed_files = len(heic_files)
        result.completed_files = sum(1 for fr in result.file_results if fr.status == "completed")

        if result.completed_files == 0:
            result.errors.append("Semua berkas HEIC gagal dikonversi.")
            result.message = "Gagal mengonversi foto HEIC/HEIF."
        elif result.completed_files < len(heic_files):
            result.warnings = result.errors.copy()
            result.message = "Konversi selesai dengan beberapa kegagalan."
        
        return result

    @staticmethod
    def _validate_file_integrity(path: Path) -> str | None:
        """Verify that a converted image file exists, is non-empty, and can be opened by Pillow."""
        if not path.exists():
            return f"File tidak ditemukan di {path}"
        if path.stat().st_size == 0:
            return "File kosong (0 byte)."
        try:
            with Image.open(path) as img:
                img.verify()
            return None
        except Exception as exc:
            return f"Format file tidak valid atau rusak: {exc}"
