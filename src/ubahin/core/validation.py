from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image

from ubahin.core.models import AppError
from ubahin.utils import ensure_writable_directory
from ubahin.utils.image_utils import SUPPORTED_IMAGE_SUFFIXES


SUPPORTED_PDF_SUFFIXES = {".pdf"}


def validate_existing_files(paths: list[Path], allowed_suffixes: set[str]) -> None:
    if not paths:
        raise AppError("Pilih minimal satu file.")
    for path in paths:
        if path.suffix.lower() not in allowed_suffixes:
            raise AppError(f"Format file tidak didukung: {path.name}")
        if not path.exists() or not path.is_file():
            raise AppError(f"File tidak ditemukan: {path.name}")
        if path.stat().st_size <= 0:
            raise AppError(f"File kosong: {path.name}")


def validate_output_dir(path: Path) -> None:
    try:
        ensure_writable_directory(path)
    except Exception as exc:
        raise AppError(f"Folder output tidak dapat ditulis: {exc}") from exc


def validate_pdf_file(path: Path) -> int:
    validate_existing_files([path], SUPPORTED_PDF_SUFFIXES)
    try:
        with fitz.open(path) as document:
            if document.needs_pass:
                raise AppError(f"PDF terkunci password: {path.name}")
            if document.page_count <= 0:
                raise AppError(f"PDF tidak memiliki halaman: {path.name}")
            return document.page_count
    except AppError:
        raise
    except Exception as exc:
        raise AppError(f"PDF rusak atau tidak dapat dibaca: {path.name}") from exc


def validate_pdf_batch(paths: list[Path], max_files: int = 50) -> int:
    if len(paths) > max_files:
        raise AppError(f"Maksimal {max_files} file PDF dalam satu antrean.")
    total_pages = 0
    for path in paths:
        total_pages += validate_pdf_file(path)
    return total_pages


def validate_image_file(path: Path) -> None:
    validate_existing_files([path], SUPPORTED_IMAGE_SUFFIXES)
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:
        raise AppError(f"Gambar rusak atau tidak dapat dibaca: {path.name}") from exc


def validate_image_batch(paths: list[Path]) -> None:
    for path in paths:
        validate_image_file(path)


def parse_page_ranges(ranges_text: str, total_pages: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for chunk in ranges_text.split(","):
        part = chunk.strip()
        if not part:
            continue
        if "-" in part:
            raw_start, raw_end = part.split("-", 1)
            start = int(raw_start.strip())
            end = int(raw_end.strip())
        else:
            start = end = int(part)
        if start < 1 or end < start or end > total_pages:
            raise AppError(f"Rentang halaman tidak valid: {part}")
        ranges.append((start, end))
    if not ranges:
        raise AppError("Rentang halaman belum diisi.")
    return ranges
