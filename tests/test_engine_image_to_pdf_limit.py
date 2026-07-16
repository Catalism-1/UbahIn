"""Regression tests for the Image to PDF 100-file batch limit at the engine boundary.

Sinkronisasi batas: React UI, pemeriksaan file Python (_inspect_image_files),
dan validasi start job (_start_image_to_pdf) semuanya harus memakai batas yang
sama (MAX_IMAGE_TO_PDF_FILES = 100).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image


def _load_engine_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "engine-python" / "engine_main.py"
    spec = importlib.util.spec_from_file_location("ubahin_engine_main_image_to_pdf_limit", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def runtime(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    engine_main = _load_engine_module()
    return engine_main.EngineRuntime(), engine_main.MAX_IMAGE_TO_PDF_FILES


def test_max_image_to_pdf_files_is_100(runtime) -> None:
    _runtime, max_files = runtime
    assert max_files == 100


def test_start_image_to_pdf_rejects_101_files(runtime, tmp_path: Path) -> None:
    engine, max_files = runtime
    files = [{"path": str(tmp_path / f"fake_{i}.png"), "file_id": str(i)} for i in range(max_files + 1)]

    response = engine._start_image_to_pdf("rid", {"files": files, "output_directory": str(tmp_path / "out")})

    assert response["ok"] is False
    assert response["error"]["code"] == "TOO_MANY_FILES"
    assert str(max_files) in response["error"]["message"]


def test_start_image_to_pdf_accepts_exactly_100_files(runtime, tmp_path: Path) -> None:
    engine, max_files = runtime
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    files = []
    for i in range(max_files):
        path = images_dir / f"img_{i:04d}.png"
        Image.new("RGB", (8, 8), (i % 256, 0, 0)).save(path)
        files.append({"path": str(path), "file_id": str(i)})

    response = engine._start_image_to_pdf(
        "rid",
        {"files": files, "output_directory": str(tmp_path / "out")},
    )

    assert response["ok"] is True, response
    assert engine._manager.wait(response["data"]["job_id"], timeout=30)


def test_inspect_image_files_does_not_silently_drop_100_files(runtime, tmp_path: Path) -> None:
    engine, max_files = runtime
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    paths = []
    for i in range(max_files):
        path = images_dir / f"img_{i:04d}.png"
        Image.new("RGB", (8, 8), (i % 256, 0, 0)).save(path)
        paths.append(str(path))

    response = engine._inspect_image_files("rid", {"paths": paths})

    assert response["ok"] is True
    assert len(response["data"]["files"]) == max_files
