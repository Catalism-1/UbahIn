from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pypdf import PdfReader, PdfWriter

from ubahin.core.cancellation import CancellationToken
from ubahin.core.models import FileResult, ServiceResult
from ubahin.core.progress import ProgressInfo
from ubahin.core.validation import parse_page_ranges, validate_output_dir, validate_pdf_file
from ubahin.utils import sanitize_filename, unique_file


@dataclass(slots=True)
class SplitPdfOptions:
    output_dir: Path
    mode: str = "all_pages"
    ranges: str = ""


class SplitPdfService:
    def split(
        self,
        pdf_file: Path,
        options: SplitPdfOptions,
        cancellation: CancellationToken | None = None,
        on_progress: Callable[[ProgressInfo], None] | None = None,
    ) -> ServiceResult:
        cancellation = cancellation or CancellationToken()
        validate_output_dir(options.output_dir)
        total_pages = validate_pdf_file(pdf_file)
        reader = PdfReader(str(pdf_file))
        if options.mode == "ranges":
            ranges = parse_page_ranges(options.ranges, total_pages)
        else:
            ranges = [(page, page) for page in range(1, total_pages + 1)]
        safe_stem = sanitize_filename(pdf_file.stem)
        result = ServiceResult(message="PDF berhasil dipisahkan.")
        for index, (start, end) in enumerate(ranges, start=1):
            cancellation.raise_if_cancelled()
            writer = PdfWriter()
            for page_number in range(start, end + 1):
                writer.add_page(reader.pages[page_number - 1])
            suffix = f"page_{start:03d}" if start == end else f"pages_{start:03d}_{end:03d}"
            output_path = unique_file(options.output_dir, f"{safe_stem}_{suffix}.pdf")
            with output_path.open("wb") as handle:
                writer.write(handle)
            result.output_paths.append(output_path)
            if on_progress:
                on_progress(
                    ProgressInfo(
                        percentage=(index / len(ranges)) * 100,
                        current_file=pdf_file.name,
                        current_item=index,
                        total_items=len(ranges),
                        message="Memisahkan PDF",
                    )
                )
        result.file_results.append(FileResult(input_path=pdf_file, output_paths=result.output_paths, output_size=result.output_size))
        return result
