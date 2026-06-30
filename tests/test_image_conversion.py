from pathlib import Path

import pytest
from PIL import Image

from ubahin.core.job_manager import JobManager
from ubahin.core.models import ToolType
from ubahin.services.image_conversion_service import ImageConversionOptions, ImageConversionService

# Pillow-HEIF is mocked or available in the environment depending on setup
# We'll create basic JPG, PNG to test universal conversion logic

def create_test_image(path: Path, format: str = "JPEG", mode: str = "RGB", size: tuple = (100, 100), color: str = "red"):
    img = Image.new(mode, size, color=color)
    img.save(path, format=format)

@pytest.fixture
def temp_workspace(tmp_path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return input_dir, output_dir

def test_image_conversion_service_jpg_to_png(temp_workspace):
    input_dir, output_dir = temp_workspace
    input_file = input_dir / "test1.jpg"
    create_test_image(input_file, format="JPEG")

    service = ImageConversionService()
    options = ImageConversionOptions(
        output_directory=str(output_dir),
        output_format="png",
        open_output_after_finish=False
    )

    result = service.convert([input_file], options)
    
    assert len(result.file_results) == 1
    assert result.file_results[0].status == "completed"
    
    output_file = Path(result.file_results[0].output_paths[0])
    assert output_file.exists()
    assert output_file.suffix.lower() == ".png"
    
    # Verify the output is a valid PNG
    with Image.open(output_file) as img:
        assert img.format == "PNG"

def test_image_conversion_service_png_to_jpg(temp_workspace):
    input_dir, output_dir = temp_workspace
    input_file = input_dir / "test2.png"
    # test transparency to jpg conversion
    create_test_image(input_file, format="PNG", mode="RGBA", color=(255, 0, 0, 128))

    service = ImageConversionService()
    options = ImageConversionOptions(
        output_directory=str(output_dir),
        output_format="jpg",
        open_output_after_finish=False
    )

    result = service.convert([input_file], options)
    
    assert len(result.file_results) == 1
    assert result.file_results[0].status == "completed"
    
    output_file = Path(result.file_results[0].output_paths[0])
    assert output_file.exists()
    assert output_file.suffix.lower() == ".jpg"
    
    # Verify the output is a valid JPG
    with Image.open(output_file) as img:
        assert img.format == "JPEG"

def test_job_manager_integration_image_convert(temp_workspace):
    input_dir, output_dir = temp_workspace
    input_file1 = input_dir / "t1.jpg"
    input_file2 = input_dir / "t2.png"
    create_test_image(input_file1, format="JPEG")
    create_test_image(input_file2, format="PNG")

    manager = JobManager()
    job = manager.create_job(
        ToolType.IMAGE_CONVERT,
        [input_file1, input_file2],
        str(output_dir),
        output_format="webp",
        open_output_after_finish=False
    )
    
    manager.start_job(job.job_id)
    # The job manager executes synchronously in test environment because start_job does not spawn threads by default
    # Wait, start_job uses ThreadPoolExecutor if run via EngineRuntime, but JobManager itself uses ThreadPoolExecutor!
    # We must wait for job to finish
    import time
    timeout = 5
    start_time = time.time()
    while job.status.value not in ('completed', 'failed', 'cancelled') and time.time() - start_time < timeout:
        time.sleep(0.1)

    assert job.status.value == "completed"
    
    output_files = list(output_dir.glob("*.webp"))
    assert len(output_files) == 2
