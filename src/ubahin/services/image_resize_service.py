from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_image_batch, validate_output_dir
from ubahin.utils import atomic_temp_path, finalize_atomic_write, remove_temp_file, unique_file
from ubahin.utils.image_utils import normalize_rgb, open_image


@dataclass(slots=True)
class ImageResizeOptions:
    output_dir: Path
    width: int | None = None
    height: int | None = None
    percent: int | None = None
    keep_ratio: bool = True
    quality: int = 90


class ImageResizeService:
    def resize(
        self,
        image_files: list[Path],
        options: ImageResizeOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        validate_output_dir(options.output_dir)
        validate_image_batch(image_files)
        result = ServiceResult(message="Ukuran gambar berhasil diubah.")
        for index, image_path in enumerate(image_files, start=1):
            cancellation.raise_if_cancelled()
            file_result = FileResult(input_path=image_path, input_size=image_path.stat().st_size)
            try:
                image = open_image(image_path)
                new_size = self._target_size(image.size, options)
                resized = image.resize(new_size, Image.Resampling.LANCZOS)
                output_path = unique_file(options.output_dir, f"{image_path.stem}_resized{image_path.suffix}")
                save_image = normalize_rgb(resized) if output_path.suffix.lower() in {".jpg", ".jpeg"} else resized
                temp_path = atomic_temp_path(output_path)
                try:
                    save_image.save(temp_path, quality=options.quality, optimize=True)
                    finalize_atomic_write(temp_path, output_path)
                except Exception:
                    remove_temp_file(temp_path)
                    raise
                image.close()
                if save_image is not resized:
                    save_image.close()
                resized.close()
                file_result.output_paths.append(output_path)
                file_result.output_size = output_path.stat().st_size
                result.output_paths.append(output_path)
            except Exception as exc:
                file_result.status = "failed"
                file_result.error = str(exc)
                result.errors.append(f"{image_path.name}: {exc}")
            result.file_results.append(file_result)
            if on_progress:
                on_progress(ProgressInfo(percentage=(index / len(image_files)) * 100, current_file=image_path.name, current_item=index, total_items=len(image_files), message="Mengubah ukuran gambar"))
        return result

    def _target_size(self, current: tuple[int, int], options: ImageResizeOptions) -> tuple[int, int]:
        width, height = current
        if options.percent:
            return max(1, width * options.percent // 100), max(1, height * options.percent // 100)
        target_width = options.width or width
        target_height = options.height or height
        if options.keep_ratio:
            ratio = min(target_width / width, target_height / height)
            return max(1, int(width * ratio)), max(1, int(height * ratio))
        return max(1, target_width), max(1, target_height)
