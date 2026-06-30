from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_output_dir
from ubahin.utils import atomic_temp_path, finalize_atomic_write, remove_temp_file, unique_file
from ubahin.utils.image_utils import normalize_rgb, open_image


@dataclass(slots=True)
class ImageConversionOptions:
    output_directory: Path
    output_format: str = "jpg"
    jpeg_quality: int = 85
    webp_quality: int = 85
    png_compression_level: int = 6
    heic_quality: int = 80
    preserve_metadata: bool = False
    open_output_after_finish: bool = True


class ImageConversionService:
    def __init__(self):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass

    def _heic_encoder_available(self) -> bool:
        try:
            import pillow_heif
            info = pillow_heif.libheif_info()
            return any("HEVC" in name or "x265" in name for name in info.get("encoders", {}).keys())
        except Exception:
            return False

    def convert(
        self,
        image_files: list[Path],
        options: ImageConversionOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        out_dir = Path(options.output_directory)
        validate_output_dir(out_dir)

        target = options.output_format.lower()
        if target in {"heic", "heif"} and not self._heic_encoder_available():
            raise ValueError("Ekspor HEIC belum tersedia pada instalasi ini.")

        suffix_map = {"jpg": ".jpg", "jpeg": ".jpg", "png": ".png", "webp": ".webp", "heic": ".heic", "heif": ".heic"}
        suffix = suffix_map.get(target, ".jpg")

        result = ServiceResult(message="Gambar berhasil dikonversi.")

        # Deduplicate by normalized path
        seen_paths = set()
        unique_files = []
        for p in image_files:
            norm = p.resolve()
            if norm not in seen_paths:
                seen_paths.add(norm)
                unique_files.append(p)

        total_files = len(unique_files)
        if total_files == 0:
            raise ValueError("Tidak ada berkas gambar untuk dikonversi.")
        if total_files > 50:
            raise ValueError(f"Maksimal 50 file per batch. Diberikan: {total_files}")

        for index, image_path in enumerate(unique_files, start=1):
            cancellation.raise_if_cancelled()
            file_result = FileResult(input_path=image_path, input_size=image_path.stat().st_size)
            try:
                if on_progress:
                    on_progress(ProgressInfo(
                        percentage=(index / total_files) * 100,
                        current_file=image_path.name,
                        current_item=index,
                        total_items=total_files,
                        message="Mengonversi gambar"
                    ))

                image = open_image(image_path)
                image = ImageOps.exif_transpose(image) # Auto orientation
                
                exif = image.getexif() if options.preserve_metadata else None
                # Strip orientation tag if preserved to avoid double rotation
                if exif and 274 in exif:
                    del exif[274]
                
                # PNG transparent to JPG white background
                if target in {"jpg", "jpeg"}:
                    image = normalize_rgb(image)
                    save_format = "JPEG"
                    save_args = {"quality": options.jpeg_quality}
                elif target == "webp":
                    # Keep alpha if exists
                    save_format = "WEBP"
                    save_args = {"quality": options.webp_quality}
                elif target == "png":
                    save_format = "PNG"
                    save_args = {"compress_level": options.png_compression_level}
                elif target in {"heic", "heif"}:
                    save_format = "HEIF"
                    save_args = {"quality": options.heic_quality}
                else:
                    save_format = "JPEG"
                    save_args = {"quality": options.jpeg_quality}
                
                if options.preserve_metadata and exif:
                    save_args["exif"] = exif.tobytes()

                output_path = unique_file(out_dir, f"{image_path.stem}{suffix}")
                temp_path = atomic_temp_path(output_path)
                try:
                    image.save(temp_path, save_format, **save_args)
                    image.close() # Close image immediately to free resources
                    
                    if not temp_path.exists() or temp_path.stat().st_size == 0:
                        raise ValueError("File temp hasil konversi kosong atau tidak ditemukan.")
                    
                    # Verify output can be opened
                    try:
                        with Image.open(temp_path) as check_img:
                            check_img.verify()
                    except Exception as e:
                        raise ValueError(f"Hasil konversi tidak valid: {e}")
                    
                    finalize_atomic_write(temp_path, output_path)
                except Exception:
                    remove_temp_file(temp_path)
                    image.close()
                    raise
                
                # Final check
                if not output_path.exists() or output_path.stat().st_size == 0:
                    raise ValueError("File output final tidak ditemukan atau kosong.")

                file_result.output_paths.append(output_path)
                file_result.output_size = output_path.stat().st_size
                result.output_paths.append(output_path)
            except Exception as exc:
                file_result.status = "failed"
                file_result.error = str(exc)
                result.errors.append(f"{image_path.name}: {exc}")
            
            result.file_results.append(file_result)

        if all(f.status == "failed" for f in result.file_results):
            raise RuntimeError("Semua konversi gambar gagal. Periksa log.")

        return result
