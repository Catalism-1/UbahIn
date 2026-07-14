"""Regression tests for _inspect_image_conversion_files.

Sebelumnya, method ini ditulis di indent salah (di luar class EngineRuntime,
nested di dalam _inspect_image), sehingga `runtime._inspect_image_conversion_files`
melempar AttributeError → seluruh batch inspect kembali sebagai generic
"Engine tidak dapat memproses request" dan UI menampilkan UNKNOWN/0 KB/
"Gagal diinspeksi" untuk file PNG yang valid.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image


def _load_engine_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "engine-python" / "engine_main.py"
    spec = importlib.util.spec_from_file_location("ubahin_engine_main", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def runtime(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    engine_main = _load_engine_module()
    return engine_main.EngineRuntime()


def test_method_is_bound_on_runtime(runtime) -> None:
    """Method harus benar-benar terikat ke instance — bukan dead code."""
    assert hasattr(runtime, "_inspect_image_conversion_files")
    assert callable(runtime._inspect_image_conversion_files)


def test_handle_request_dispatches_to_inspect(runtime, tmp_path: Path) -> None:
    """Aksi `inspect_image_conversion_files` via handle_request menghasilkan ok=True."""
    png = tmp_path / "valid.png"
    Image.new("RGB", (40, 40), "red").save(png, "PNG")

    response = runtime.handle_request(
        {
            "id": "req-1",
            "action": "inspect_image_conversion_files",
            "payload": {"paths": [str(png)]},
        }
    )

    assert response["ok"] is True, response
    assert response["id"] == "req-1"
    files = response["data"]["files"]
    assert len(files) == 1
    assert files[0]["status"] == "ready"
    assert files[0]["format"] == "PNG"
    assert files[0]["size_bytes"] > 0
    assert files[0]["thumbnail_data_uri"].startswith("data:image/jpeg;base64,")


def test_valid_png_returns_ready_with_metadata(runtime, tmp_path: Path) -> None:
    png = tmp_path / "sample, with comma.png"
    Image.new("RGB", (123, 45), "green").save(png, "PNG")

    response = runtime._inspect_image_conversion_files("rid", {"paths": [str(png)]})
    file_info = response["data"]["files"][0]

    assert file_info["status"] == "ready"
    assert file_info["format"] == "PNG"
    assert file_info["width"] == 123
    assert file_info["height"] == 45
    assert file_info["size_bytes"] == png.stat().st_size
    assert file_info["error"] is None
    assert file_info["error_code"] is None


def test_empty_file_returns_specific_error_code(runtime, tmp_path: Path) -> None:
    empty = tmp_path / "kosong.png"
    empty.touch()

    response = runtime._inspect_image_conversion_files("rid", {"paths": [str(empty)]})
    file_info = response["data"]["files"][0]

    assert file_info["status"] == "failed"
    assert file_info["error_code"] == "FILE_EMPTY"
    assert file_info["format"] is None
    assert file_info["thumbnail_data_uri"] is None
    assert "kosong" in file_info["error"].lower()


def test_missing_file_returns_not_found(runtime) -> None:
    response = runtime._inspect_image_conversion_files(
        "rid", {"paths": ["Z:/definitely/nowhere/missing.png"]}
    )
    file_info = response["data"]["files"][0]

    assert file_info["status"] == "failed"
    assert file_info["error_code"] == "FILE_NOT_FOUND"


def test_corrupt_image_returns_corrupt_code(runtime, tmp_path: Path) -> None:
    corrupt = tmp_path / "rusak.png"
    corrupt.write_bytes(b"NOT A PNG" * 50)

    response = runtime._inspect_image_conversion_files("rid", {"paths": [str(corrupt)]})
    file_info = response["data"]["files"][0]

    assert file_info["status"] == "failed"
    assert file_info["error_code"] == "IMAGE_CORRUPT"
    # Ukuran asli tetap dilaporkan supaya UI bisa menjelaskan "450 byte tapi rusak".
    assert file_info["size_bytes"] == corrupt.stat().st_size


def test_mixed_batch_does_not_contaminate_valid_files(runtime, tmp_path: Path) -> None:
    valid = tmp_path / "good.png"
    Image.new("RGB", (10, 10), "blue").save(valid, "PNG")
    empty = tmp_path / "kosong.png"
    empty.touch()
    corrupt = tmp_path / "rusak.png"
    corrupt.write_bytes(b"junk" * 20)

    response = runtime._inspect_image_conversion_files(
        "rid", {"paths": [str(valid), str(empty), str(corrupt)]}
    )
    by_name = {f["filename"]: f for f in response["data"]["files"]}

    assert by_name["good.png"]["status"] == "ready"
    assert by_name["good.png"]["format"] == "PNG"
    assert by_name["kosong.png"]["status"] == "failed"
    assert by_name["rusak.png"]["status"] == "failed"


def test_unicode_filename_inspects(runtime, tmp_path: Path) -> None:
    unicode_path = tmp_path / "café_ñiño.jpg"
    Image.new("RGB", (50, 30), "purple").save(unicode_path, "JPEG")

    response = runtime._inspect_image_conversion_files("rid", {"paths": [str(unicode_path)]})
    file_info = response["data"]["files"][0]

    assert file_info["status"] == "ready"
    assert file_info["format"] == "JPEG"


def test_invalid_payload_returns_error(runtime) -> None:
    response = runtime._inspect_image_conversion_files("rid", {"paths": "not a list"})
    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_PAYLOAD"
