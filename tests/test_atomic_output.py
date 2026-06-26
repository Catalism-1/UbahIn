from __future__ import annotations

from pathlib import Path

from ubahin.utils import atomic_temp_path, finalize_atomic_write, unique_file


def test_atomic_output_helper(tmp_path: Path) -> None:
    final = unique_file(tmp_path, "hasil.txt")
    temp = atomic_temp_path(final)
    temp.write_text("ok", encoding="utf-8")
    finalize_atomic_write(temp, final)
    assert final.read_text(encoding="utf-8") == "ok"
    assert not temp.exists()
