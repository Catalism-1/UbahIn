from __future__ import annotations

import zipfile
from pathlib import Path

from ubahin.utils import unique_file


class ZipService:
    def create_zip(self, output_dir: Path, files: list[Path], name: str = "Ubahin_Hasil.zip") -> Path:
        zip_path = unique_file(output_dir, name)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for file_path in files:
                if file_path.exists() and file_path.is_file():
                    archive.write(file_path, arcname=file_path.relative_to(output_dir))
        return zip_path
