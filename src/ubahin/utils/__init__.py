from __future__ import annotations

from .disk_utils import available_disk_bytes, ensure_writable_directory, has_enough_space
from .file_utils import (
    coerce_paths,
    coerce_pdf_paths,
    file_size,
    human_size,
    open_in_file_manager,
)
from .logger import get_logger, setup_logging
from .path_utils import (
    app_data_dir,
    atomic_temp_path,
    finalize_atomic_write,
    get_app_data_dir,
    get_log_dir,
    get_resource_path,
    is_frozen_app,
    remove_temp_file,
    sanitize_filename,
    unique_directory,
    unique_file,
)


def estimated_output_bytes(pages: int, dpi: int, jpeg_quality: int) -> int:
    dpi_factor = (dpi / 150) ** 2
    quality_factor = 0.7 + ((jpeg_quality - 70) / 25) * 0.6
    return int(pages * 300_000 * dpi_factor * quality_factor)


__all__ = [
    "app_data_dir",
    "atomic_temp_path",
    "available_disk_bytes",
    "coerce_paths",
    "coerce_pdf_paths",
    "ensure_writable_directory",
    "estimated_output_bytes",
    "file_size",
    "finalize_atomic_write",
    "get_app_data_dir",
    "get_logger",
    "get_log_dir",
    "get_resource_path",
    "has_enough_space",
    "human_size",
    "is_frozen_app",
    "open_in_file_manager",
    "remove_temp_file",
    "sanitize_filename",
    "setup_logging",
    "unique_directory",
    "unique_file",
]
