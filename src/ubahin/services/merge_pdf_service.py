from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pypdf import PdfReader, PdfWriter

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_output_dir, validate_pdf_batch
from ubahin.utils import unique_file


@dataclass(slots=True)
class MergePdfOptions:
    output_dir: Path
    output_name: str = "gabungan.pdf"


class MergePdfService:
    def merge(
        self,
        pdf_files: list[Path],
        options: MergePdfOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        validate_output_dir(options.output_dir)
        total_pages = validate_pdf_batch(pdf_files, max_files=999)
        writer = PdfWriter()
        completed = 0
        for file_index, pdf_path in enumerate(pdf_files, start=1):
            cancellation.raise_if_cancelled()
            reader = PdfReader(str(pdf_path))
            for page in reader.pages:
                cancellation.raise_if_cancelled()
                writer.add_page(page)
                completed += 1
                if on_progress:
                    on_progress(
                        ProgressInfo(
                            percentage=(completed / max(total_pages, 1)) * 100,
                            current_file=pdf_path.name,
                            current_item=file_index,
                            total_items=len(pdf_files),
                            current_page=completed,
                            total_pages=total_pages,
                            message="Menggabungkan PDF",
                        )
                    )
        output_path = unique_file(options.output_dir, options.output_name)
        with output_path.open("wb") as handle:
            writer.write(handle)
        return ServiceResult(
            output_paths=[output_path],
            file_results=[FileResult(input_path=pdf_files[0], output_paths=[output_path], output_size=output_path.stat().st_size)],
            message="PDF berhasil digabungkan.",
        )
