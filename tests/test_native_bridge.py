from __future__ import annotations

from pathlib import Path

from ubahin.native_bridge import fast_file_hash, native_status, safe_output_path, scan_files, system_snapshot


def test_native_bridge_python_fallback(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("ubahin", encoding="utf-8")
    status = native_status()
    assert status["backend"] in {"python", "rust"}
    assert len(fast_file_hash(sample)) == 64
    scanned = scan_files([sample])
    assert scanned[0]["exists"] is True
    assert Path(safe_output_path(tmp_path, "a:b.txt")).name == "a_b.txt"
    assert "logical_cpu_count" in system_snapshot(tmp_path)
