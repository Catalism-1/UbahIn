# UbahIn

Aplikasi desktop Windows untuk mengubah, menggabungkan, dan mengelola PDF/gambar secara lokal —
tanpa upload file ke server mana pun.

[![Latest Release](https://img.shields.io/github/v/release/Catalism-1/UbahIn?label=Release)](https://github.com/Catalism-1/UbahIn/releases/latest)
[![Windows 10/11 x86 & x64](https://img.shields.io/badge/OS-Windows%2010%20%7C%2011%20x86%20%26%20x64-blue?logo=windows)](#)
[![Installer](https://img.shields.io/badge/Download-Installer-brightgreen?logo=windows)](https://github.com/Catalism-1/UbahIn/releases/latest)

[**⬇️ Download UbahIn Installer (.exe)**](https://github.com/Catalism-1/UbahIn/releases/latest)

## Kenapa UbahIn

- **Offline/local** — semua konversi berjalan di komputer Anda, tidak ada koneksi internet yang dibutuhkan.
- **Privasi dokumen** — file tidak pernah dikirim ke server manapun untuk fitur inti.
- **Cepat untuk workflow harian** — dirancang untuk kebutuhan konversi PDF/gambar sehari-hari.
- **Desktop app modern** — dibangun dengan Tauri 2, ringan dan native di Windows.
- **Engine Python** — proses konversi PDF/gambar ditangani oleh engine Python yang matang dan teruji.

## Fitur (v0.1.2)

- PDF ke JPG
- Gambar ke PDF
- Ubah Format Gambar
- Gabungkan PDF
- Riwayat lokal (history)
- Pengaturan lokal (settings)
- Diagnostik engine
- Dark mode
- Engine auto-check saat startup aplikasi

### Coming Soon

- Split PDF
- Compress PDF
- Image Resize
- Image Compress
- OCR lokal/offline
- Watermark / page tools

## Arsitektur

```text
React + TypeScript UI (desktop-tauri/src)
  -> Tauri 2 / Rust command boundary (desktop-tauri/src-tauri)
  -> Python sidecar engine, JSON Lines via stdio (engine-python/engine_main.py)
  -> file lokal + SQLite history + JSON settings
```

Prinsip:

- React tidak menyentuh filesystem, SQLite, atau engine secara langsung — semua lewat command Tauri.
- Rust/Tauri hanya menjadi boundary native: command bridge, lifecycle sidecar, dan packaging.
- Python adalah pemilik logika konversi, validasi output, job lifecycle, history, settings, dan error handling.
- Tidak ada HTTP API dan tidak ada dependency cloud — aplikasi sepenuhnya offline/local.

Detail migrasi arsitektur ada di [`docs/TAURI_MIGRATION.md`](docs/TAURI_MIGRATION.md).

## Cara Instalasi (pengguna)

1. Kunjungi [halaman rilis terbaru](https://github.com/Catalism-1/UbahIn/releases/latest).
2. Unduh installer `.exe`.
3. Jalankan file yang diunduh, klik **Install**.
4. Aplikasi UbahIn dapat diakses lewat shortcut Desktop atau Start Menu.

## Menjalankan Development

Prasyarat: Python 3.11+, Node.js, Rust toolchain (untuk build Tauri).

```bat
:: Setup virtual environment Python (sekali saja)
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: Jalankan test Python
.venv\Scripts\python.exe -m pytest

:: Jalankan UI Tauri dalam mode dev
cd desktop-tauri
npm install
npm run dev
```

## Build / Release

```bat
build_release_windows.bat
```

Script ini akan: install dependency Python, build sidecar Python (`engine-python/build_engine.bat`),
menjalankan test Python, install dependency npm, build & typecheck frontend, lalu menjalankan
`npm run tauri build`. Installer NSIS hasil build ada di:

```text
desktop-tauri\src-tauri\target\release\bundle\nsis\
```

## Test

```bat
.venv\Scripts\python.exe -m pytest
```

```bat
cd desktop-tauri
cmd /c npm run build
```

## Privasi

- File diproses sepenuhnya secara lokal di perangkat pengguna.
- Tidak ada upload dokumen ke server untuk fitur inti.
- History dan settings tersimpan di app data lokal Windows (bukan cloud).

## Status Release

`v0.1.2`

## Screenshot

Coming soon.

## Roadmap

Lihat bagian [Coming Soon](#coming-soon) di atas untuk fitur yang direncanakan setelah v0.1.2.

## Cara Melaporkan Bug

1. Buka tab [Issues](https://github.com/Catalism-1/UbahIn/issues).
2. Klik **New Issue** dan pilih template **Bug Report**.
3. Isi informasi yang diperlukan sesuai dengan form yang muncul.

## Riwayat Aplikasi

Generasi UI sebelumnya (CustomTkinter/pywebview + PyInstaller) sudah tidak aktif dikembangkan dan
diarsipkan di [`legacy/pywebview-or-tkinter-ui-backup/`](legacy/pywebview-or-tkinter-ui-backup/).

## License

License belum ditentukan.
