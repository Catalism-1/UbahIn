# Ubahin

Ubahin adalah backend converter file lokal/offline untuk Windows. Fokusnya adalah proses konversi yang stabil, antrean pekerjaan yang aman, dan paket aplikasi portable/installer yang bisa dijalankan pengguna akhir tanpa menginstal Python secara manual.

Semua proses berjalan lokal. Tidak ada upload file, API cloud, database eksternal, atau koneksi internet yang dibutuhkan saat aplikasi dipakai.

## Fitur Utama

- PDF ke JPG sampai 50 PDF per antrean.
- Render PDF satu per satu dengan PyMuPDF agar RAM tidak melonjak.
- DPI output: 120, 150, 200, dan 300.
- Kualitas JPG: 70, 80, 90, dan 95.
- Mode performa: hemat RAM, seimbang, dan cepat.
- Background worker, cancellation token, dan status job yang jelas.
- Jika satu file gagal, file berikutnya tetap diproses.
- Validasi PDF rusak, PDF terkunci, file tidak terbaca, output tidak bisa ditulis, dan estimasi ruang disk.
- Nama file aman untuk Windows dan anti-tertimpa dengan suffix otomatis.
- Atomic write untuk mengurangi risiko file hasil setengah jadi.
- Log proses dan error ke `conversion_log.txt`.
- ZIP hasil konversi.
- Riwayat lokal SQLite dengan migrasi schema dan retention.
- Logging aplikasi di folder data lokal pengguna.
- Optional native module Rust/PyO3 dengan fallback Python otomatis.

## Struktur Project

```text
Ubahin/
├── main.py
├── src/ubahin/
│   ├── core/
│   ├── services/
│   ├── ui_bridge/
│   ├── utils/
│   └── native_bridge.py
├── native/
│   └── ubahin_native/
├── tests/
├── scripts/
├── assets/
├── .github/workflows/
├── build_portable.bat
├── build_installer.bat
├── installer_script.iss
├── requirements.txt
└── pyproject.toml
```

## Menjalankan Source Code

Gunakan Python 3.11 atau lebih baru.

```bat
cd "D:\Projek Pribadi Kode\convert_pdf\Ubahin_backend_foundation\Ubahin"
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py main.py "C:\PDF\contoh.pdf" -o "C:\Hasil Ubahin" --preset high --zip
```

## Membuat EXE Portable

Jalankan:

```bat
build_portable.bat
```

Hasil build ada di:

```text
dist\Ubahin\Ubahin.exe
```

Folder `dist\Ubahin` adalah versi portable. Folder ini bisa disalin ke laptop Windows lain dan dijalankan tanpa instalasi Python.

## Membuat Installer

Install Inno Setup 6 terlebih dahulu, lalu jalankan:

```bat
build_installer.bat
```

Hasil installer ada di:

```text
dist\installer\Ubahin_Setup.exe
```

Installer akan membuat shortcut Desktop dan Start Menu dengan nama aplikasi `Ubahin`.

## Native Rust Opsional

Folder `native/ubahin_native` berisi modul Rust/PyO3 opsional untuk akselerasi helper seperti hashing, sanitasi path, snapshot sistem, dan estimasi ukuran. Jika modul native tidak tersedia, aplikasi otomatis memakai fallback Python dari `src/ubahin/native_bridge.py`.

Build native lokal membutuhkan Rust toolchain dan Maturin:

```bat
py -m pip install maturin
cd native\ubahin_native
maturin develop --release
```

Workflow GitHub Actions juga menyiapkan Rust dan membangun wheel native di Windows runner.

## Quality Gate

Perintah yang dipakai untuk pengecekan lokal:

```bat
py -m ruff check src tests
py -m pytest
py scripts\benchmark_smoke.py
dist\Ubahin\Ubahin.exe --help
```

## CI dan Release

Workflow tersedia di:

- `.github/workflows/ci.yml` untuk lint, test, dan smoke import.
- `.github/workflows/build-windows.yml` untuk build Windows, artefak portable, installer, dan release saat tag `v*`.

## Catatan Keterbatasan

- Modul native Rust bersifat opsional. Tanpa Rust, aplikasi tetap berjalan dengan fallback Python.
- PDF ke Word, Word ke PDF kompleks, dan OCR belum diimplementasikan agar aplikasi tidak memberi hasil yang menyesatkan.
- Build lokal installer membutuhkan Inno Setup 6 tersedia di PATH atau lokasi instalasi standar.
