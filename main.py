"""Titik masuk sementara untuk mesin Ubahin tanpa GUI.

GUI nanti cukup mengimpor `ConversionManager` dari package `ubahin`.
"""
from ubahin.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
