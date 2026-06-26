from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

import fitz

from .models import ConversionOptions, FileTask, TaskStatus
from .utils import sanitize_filename, unique_directory


class ConversionCancelled(Exception):
    """Dilempar ketika pengguna membatalkan antrean konversi."""


class PdfReadError(Exception):
    """Error pembacaan PDF yang siap ditampilkan ke pengguna."""


PageProgressCallback = Callable[[FileTask], None]
MessageCallback = Callable[[str, dict[str, object]], None]


@dataclass(frozen=True, slots=True)
class PdfInspection:
    page_count: int
    file_size: int


def inspect_pdf(path: Path) -> PdfInspection:
    if path.suffix.lower() != ".pdf":
        raise PdfReadError("File bukan PDF.")
    if not path.exists() or not path.is_file():
        raise PdfReadError("File tidak ditemukan atau tidak dapat dibaca.")
    try:
        with fitz.open(path) as document:
            if document.needs_pass:
                raise PdfReadError("PDF dilindungi password dan belum dapat diproses.")
            return PdfInspection(page_count=document.page_count, file_size=path.stat().st_size)
    except PdfReadError:
        raise
    except (fitz.FileDataError, RuntimeError, OSError) as exc:
        raise PdfReadError(f"PDF rusak atau tidak dapat dibaca: {exc}") from exc


def convert_pdf_to_jpg(
    task: FileTask,
    options: ConversionOptions,
    cancel_event: Event,
    on_page_progress: PageProgressCallback | None = None,
    on_message: MessageCallback | None = None,
) -> FileTask:
    """Konversi satu PDF, satu halaman pada satu waktu untuk menjaga penggunaan RAM."""
    if cancel_event.is_set():
        task.status = TaskStatus.CANCELLED
        return task

    task.status = TaskStatus.PROCESSING
    source = task.source_path
    output_folder = unique_directory(options.output_dir, sanitize_filename(source.stem))
    task.output_dir = output_folder
    scale = options.dpi / 72.0
    matrix = fitz.Matrix(scale, scale)

    try:
        with fitz.open(source) as document:
            if document.needs_pass:
                raise PdfReadError("PDF dilindungi password dan belum dapat diproses.")

            task.pages_total = document.page_count
            for index in range(document.page_count):
                if cancel_event.is_set():
                    task.status = TaskStatus.CANCELLED
                    if on_message:
                        on_message("task_cancelled", {"task_id": task.task_id, "filename": task.filename})
                    return task

                page = document.load_page(index)
                pixmap = page.get_pixmap(
                    matrix=matrix,
                    colorspace=fitz.csRGB,
                    alpha=False,
                )
                output_path = output_folder / f"{sanitize_filename(source.stem)}_page_{index + 1:03d}.jpg"
                # PyMuPDF menulis JPEG tanpa perlu menyimpan seluruh PDF di RAM.
                pixmap.save(str(output_path), jpg_quality=options.jpeg_quality)
                del pixmap

                task.output_files.append(output_path)
                task.pages_done = index + 1
                if on_page_progress:
                    on_page_progress(task)

        task.status = TaskStatus.COMPLETED
        return task
    except ConversionCancelled:
        task.status = TaskStatus.CANCELLED
        return task
    except (PdfReadError, fitz.FileDataError, RuntimeError, OSError) as exc:
        task.status = TaskStatus.FAILED
        task.error_message = str(exc)
        return task
