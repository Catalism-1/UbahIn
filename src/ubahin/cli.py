from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .events import AppEvent
from .manager import ConversionManager
from .models import ConversionOptions, PerformanceMode, QualityPreset
from .utils import human_size


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ubahin",
        description="Ubahin — PDF ke JPG lokal tanpa upload internet.",
    )
    parser.add_argument("inputs", nargs="+", help="Satu atau beberapa file PDF.")
    parser.add_argument("-o", "--output", required=True, help="Folder hasil.")
    parser.add_argument("--preset", choices=[item.value for item in QualityPreset], default="high")
    parser.add_argument("--dpi", choices=[120, 150, 200, 300], type=int)
    parser.add_argument("--jpg-quality", choices=[70, 80, 90, 95], type=int)
    parser.add_argument("--mode", choices=[item.value for item in PerformanceMode], default="seimbang")
    parser.add_argument("--zip", action="store_true", help="Buat ZIP hasil setelah selesai.")
    parser.add_argument("--json", action="store_true", help="Cetak ringkasan dalam JSON.")
    return parser


def _print_event(event: AppEvent) -> None:
    if event.kind == "file_progress":
        payload = event.payload
        text = (
            f"\rMemproses {payload['filename']}: "
            f"halaman {payload['file_pages_done']}/{payload['file_pages_total']} "
            f"| total {payload['completed_pages']}/{payload['total_pages']}"
        )
        print(text, end="", flush=True)
    elif event.kind == "file_completed":
        print(f"\n✓ Selesai: {event.payload['filename']} ({event.payload['output_count']} JPG)")
    elif event.kind == "file_failed":
        print(f"\n✗ Gagal: {event.payload['filename']} — {event.payload['error']}", file=sys.stderr)
    elif event.kind == "job_started":
        print(f"Mulai mengubah {event.payload['total_files']} PDF ({event.payload['total_pages']} halaman).")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)
    options = ConversionOptions(
        output_dir=Path(args.output),
        quality_preset=QualityPreset(args.preset),
        dpi=args.dpi,
        jpeg_quality=args.jpg_quality,
        performance_mode=PerformanceMode(args.mode),
        create_zip=args.zip,
    )

    manager = ConversionManager()
    if not args.json:
        manager.add_listener(_print_event)

    try:
        job = manager.create_pdf_to_jpg_job(args.inputs, options)
        manager.start(job.job_id)
        manager.wait(job.job_id)
        final_job = manager.get_job(job.job_id)
    except (ValueError, PermissionError, OSError) as exc:
        print(f"Gagal memulai: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(final_job.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("\n\nRingkasan")
        print(f"Berhasil: {final_job.success_count} file")
        print(f"Gagal: {final_job.failure_count} file")
        print(f"JPG dibuat: {final_job.total_output_files}")
        print(f"Folder hasil: {final_job.options.output_dir}")
        if final_job.zip_path:
            print(f"ZIP hasil: {final_job.zip_path} ({human_size(final_job.zip_path.stat().st_size)})")

    return 0 if final_job.status.value in {"completed", "completed_with_errors"} else 1
