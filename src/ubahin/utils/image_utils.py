from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def open_image(path: Path) -> Image.Image:
    image = Image.open(path)
    return ImageOps.exif_transpose(image)


def normalize_rgb(image: Image.Image, background: str = "white") -> Image.Image:
    if image.mode in {"RGBA", "LA"}:
        canvas = Image.new("RGB", image.size, background)
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        canvas.paste(image, mask=alpha)
        return canvas
    if image.mode != "RGB":
        return image.convert("RGB")
    return image
