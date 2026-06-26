from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_image_batch, validate_output_dir
from ubahin.utils import atomic_temp_path, finalize_atomic_write, remove_temp_file, unique_file
from ubahin.utils.image_utils import normalize_rgb, open_image


@dataclass(slots=True)
class ImageConvertOptions:
    output_dir: Path
    target_format: str = "JPEG"
    quality: int = 90


class ImageConvertService:
    def convert(
        self,
        image_files: list[Path],
        options: ImageConvertOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        validate_output_dir(options.output_dir)
        validate_image_batch(image_files)
        result = ServiceResult(message="Gambar berhasil dikonversi.")
        target = options.target_format.upper()
        suffix = ".jpg" if target in {"JPG", "JPEG"} else f".{target.lower()}"
        for index, image_path in enumerate(image_files, start=1):
            cancellation.raise_if_cancelled()
            file_result = FileResult(input_path=image_path, input_size=image_path.stat().st_size)
            try:
                image = open_image(image_path)
                if target in {"JPG", "JPEG"}:
                    image = normalize_rgb(image)
                    save_format = "JPEG"
                else:
                    save_format = target
                output_path = unique_file(options.output_dir, f"{image_path.stem}{suffix}")
                save_args = {"quality": options.quality} if save_format in {"JPEG", "WEBP"} else {}
                temp_path = atomic_temp_path(output_path)
                try:
                    image.save(temp_path, save_format, **save_args)
                    finalize_atomic_write(temp_path, output_path)
                except Exception:
                    remove_temp_file(temp_path)
                    raise
                image.close()
                file_result.output_paths.append(output_path)
                file_result.output_size = output_path.stat().st_size
                result.output_paths.append(output_path)
            except Exception as exc:
                file_result.status = "failed"
                file_result.error = str(exc)
                result.errors.append(f"{image_path.name}: {exc}")
            result.file_results.append(file_result)
            if on_progress:
                on_progress(ProgressInfo(percentage=(index / len(image_files)) * 100, current_file=image_path.name, current_item=index, total_items=len(image_files), message="Mengubah format gambar"))
        return result
