from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INVALID_FILE = "INVALID_FILE"
    PASSWORD_PROTECTED = "PASSWORD_PROTECTED"
    OUTPUT_NOT_WRITABLE = "OUTPUT_NOT_WRITABLE"
    INSUFFICIENT_DISK_SPACE = "INSUFFICIENT_DISK_SPACE"
    OUT_OF_MEMORY_RISK = "OUT_OF_MEMORY_RISK"
    JOB_CANCELLED = "JOB_CANCELLED"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    NATIVE_CORE_UNAVAILABLE = "NATIVE_CORE_UNAVAILABLE"


USER_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.FILE_NOT_FOUND: "File tidak ditemukan.",
    ErrorCode.INVALID_FILE: "File tidak valid atau tidak didukung.",
    ErrorCode.PASSWORD_PROTECTED: "File dilindungi password.",
    ErrorCode.OUTPUT_NOT_WRITABLE: "Folder hasil tidak dapat ditulis.",
    ErrorCode.INSUFFICIENT_DISK_SPACE: "Ruang penyimpanan tidak cukup.",
    ErrorCode.OUT_OF_MEMORY_RISK: "Memori bebas terlalu rendah untuk proses ini.",
    ErrorCode.JOB_CANCELLED: "Proses dibatalkan.",
    ErrorCode.CONVERSION_FAILED: "Konversi gagal.",
    ErrorCode.NATIVE_CORE_UNAVAILABLE: "Native core belum aktif, aplikasi memakai mode Python.",
}


def user_message(code: ErrorCode) -> str:
    return USER_MESSAGES.get(code, "Terjadi kesalahan.")
