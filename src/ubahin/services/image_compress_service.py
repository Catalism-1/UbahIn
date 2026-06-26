from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_image_batch, validate_output_dir
from ubahin.utils import unique_file
from ubahin.utils.image_utils import normalize_rgb, open_image


@dataclass(slots=True)
class ImageCompressOptions:
    output_dir: Path
    quality: int = 80


class ImageCompressService:
    def compress(
        self,
        image_files: list[Path],
        options: ImageCompressOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        if options.quality not in {60, 70, 80, 90, 95}:
            raise ValueError("Kualitas gambar harus salah satu dari 60, 70, 80, 90, atau 95.")
        cancellation = cancellation or CancellationToken()
        validate_output_dir(options.output_dir)
        validate_image_batch(image_files)
        result = ServiceResult(message="Gambar berhasil dikompres.")
        for index, image_path in enumerate(image_files, start=1):
            cancellation.raise_if_cancelled()
            file_result = FileResult(input_path=image_path, input_size=image_path.stat().st_size)
            try:
                image = open_image(image_path)
                suffix = image_path.suffix.lower()
                output_path = unique_file(options.output_dir, f"{image_path.stem}_compressed{suffix}")
                save_image = normalize_rgb(image) if suffix in {".jpg", ".jpeg"} else image
                save_image.save(output_path, quality=options.quality, optimize=True)
                image.close()
                if save_image is not image:
                    save_image.close()
                file_result.output_paths.append(output_path)
                file_result.output_size = output_path.stat().st_size
                result.output_paths.append(output_path)
            except Exception as exc:
                file_result.status = "failed"
                file_result.error = str(exc)
                result.errors.append(f"{image_path.name}: {exc}")
            result.file_results.append(file_result)
            if on_progress:
                on_progress(ProgressInfo(percentage=(index / len(image_files)) * 100, current_file=image_path.name, current_item=index, total_items=len(image_files), message="Mengompres gambar"))
        return result
