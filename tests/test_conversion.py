from __future__ import annotations

from pathlib import Path

import fitz

from ubahin.manager import ConversionManager
from ubahin.models import ConversionOptions, PerformanceMode, QualityPreset


def create_pdf(path: Path, pages: int = 2) -> None:
    document = fitz.open()
    for number in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), f"Ubahin test page {number + 1}")
    document.save(path)
    document.close()


def test_pdf_to_jpg_and_zip(tmp_path: Path) -> None:
    pdf = tmp_path / "contoh dokumen.pdf"
    create_pdf(pdf, pages=2)
    output = tmp_path / "hasil"
    manager = ConversionManager()
    job = manager.create_pdf_to_jpg_job(
        [pdf],
        ConversionOptions(
            output_dir=output,
            quality_preset=QualityPreset.STANDARD,
            performance_mode=PerformanceMode.RAM_SAVER,
            create_zip=True,
        ),
    )
    manager.start(job.job_id)
    assert manager.wait(job.job_id, timeout=20)

    final = manager.get_job(job.job_id)
    assert final.success_count == 1
    assert final.total_output_files == 2
    assert final.zip_path is not None and final.zip_path.exists()
    assert all(path.exists() for path in final.tasks[0].output_files)
