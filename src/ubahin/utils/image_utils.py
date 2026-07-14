from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def open_image(path: Path) -> Image.Image:
    image = Image.open(path)
    return ImageOps.exif_transpose(image)


def normalize_rgb(image: Image.Image, background: str = "white") -> Image.Image:
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba_image = image.convert("RGBA")
        canvas = Image.new("RGB", rgba_image.size, background)
        alpha = rgba_image.getchannel("A")
        canvas.paste(rgba_image, mask=alpha)
        return canvas
    if image.mode != "RGB":
        return image.convert("RGB")
    return image
