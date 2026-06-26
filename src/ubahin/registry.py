from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    tool_id: str
    label: str
    category: str
    description: str
    status: str  # ready | coming_soon


TOOL_CATALOG: tuple[ToolDefinition, ...] = (
    ToolDefinition("pdf_to_jpg", "PDF ke JPG", "Ubah PDF", "Ubah setiap halaman PDF menjadi JPG.", "ready"),
    ToolDefinition("image_to_pdf", "Gambar ke PDF", "Ubah PDF", "Gabungkan gambar menjadi file PDF.", "ready"),
    ToolDefinition("merge_pdf", "Gabungkan PDF", "Ubah PDF", "Satukan beberapa PDF menjadi satu file.", "ready"),
    ToolDefinition("split_pdf", "Pisahkan PDF", "Ubah PDF", "Pisahkan halaman PDF ke file terpisah.", "ready"),
    ToolDefinition("compress_pdf", "Kompres PDF", "Ubah PDF", "Optimalkan ukuran PDF secara lokal.", "ready"),
    ToolDefinition("pdf_to_word", "PDF ke Word", "Ubah PDF", "Ekspor PDF ke dokumen Word.", "coming_soon"),
    ToolDefinition("word_to_pdf", "Word ke PDF", "Ubah PDF", "Ubah dokumen Word menjadi PDF.", "coming_soon"),
    ToolDefinition("ocr", "OCR", "Dokumen", "Ambil teks dari gambar atau PDF scan.", "coming_soon"),
    ToolDefinition("image_convert", "Ubah Format Gambar", "Ubah Gambar", "Ubah JPG, PNG, WEBP, dan format gambar umum.", "ready"),
    ToolDefinition("image_compress", "Kompres Gambar", "Ubah Gambar", "Perkecil ukuran gambar.", "ready"),
    ToolDefinition("image_resize", "Ubah Ukuran Gambar", "Ubah Gambar", "Atur ukuran gambar dengan mudah.", "ready"),
)
