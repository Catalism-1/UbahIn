from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import fitz

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import validate_output_dir, validate_pdf_file
from ubahin.utils import unique_file


@dataclass(slots=True)
class CompressPdfOptions:
    output_dir: Path
    preset: str = "Seimbang"
    keep_if_larger: bool = False


class CompressPdfService:
    def compress(
        self,
        pdf_file: Path,
        options: CompressPdfOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        validate_output_dir(options.output_dir)
        validate_pdf_file(pdf_file)
        input_size = pdf_file.stat().st_size
        output_path = unique_file(options.output_dir, f"{pdf_file.stem}_compressed.pdf")
        garbage = {"Ringan": 2, "Seimbang": 3, "Maksimal": 4}.get(options.preset, 3)
        with fitz.open(pdf_file) as document:
            cancellation.raise_if_cancelled()
            document.save(output_path, garbage=garbage, deflate=True, clean=True)
        output_size = output_path.stat().st_size
        message = "PDF berhasil dikompres."
        if output_size >= input_size and not options.keep_if_larger:
            output_path.unlink(missing_ok=True)
            message = "Kompresi tidak menghemat ukuran. File hasil tidak disimpan."
            return ServiceResult(
                file_results=[FileResult(input_path=pdf_file, status="skipped", input_size=input_size, output_size=output_size)],
                message=message,
            )
        if on_progress:
            on_progress(ProgressInfo(percentage=100, current_file=pdf_file.name, message=message))
        return ServiceResult(
            output_paths=[output_path],
            file_results=[FileResult(input_path=pdf_file, output_paths=[output_path], input_size=input_size, output_size=output_size)],
            message=message,
        )
