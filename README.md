# Ubahin: Konverter File Lokal Super Cepat

Ubahin adalah aplikasi backend konverter file PDF ke gambar (JPG) secara offline dan aman untuk Windows. Semua proses dilakukan langsung di dalam komputer Anda tanpa perlu koneksi internet, memastikan privasi dokumen Anda terjaga.

[![Latest Release](https://img.shields.io/github/v/release/Catalism-1/UbahIn?label=Release)](https://github.com/Catalism-1/UbahIn/releases/latest)
[![Windows 10/11 x64](https://img.shields.io/badge/OS-Windows%2010%20%7C%2011%20x64-blue?logo=windows)](#)

[**⬇️ Download untuk Windows**](https://github.com/Catalism-1/UbahIn/releases/latest)

## Fitur

- Konversi PDF ke JPG secara lokal/offline.
- Pilihan kualitas Standard, Tinggi, dan Sangat Tinggi.
- Dukungan antrean konversi file hingga 50 dokumen sekaligus.
- Indikator progres yang real-time dan opsi pembatalan.
- Mengekspor hasil konversi ke dalam satu file ZIP secara otomatis.
- Installer mandiri atau versi portable.

## Cara Instalasi

1. Kunjungi [halaman rilis terbaru](https://github.com/Catalism-1/UbahIn/releases/latest).
2. Unduh `Ubahin_Setup.exe`.
3. Jalankan file yang diunduh.
4. Klik **Install** dan kemudian klik **Finish** setelah selesai.
5. Aplikasi Ubahin akan langsung terbuka, atau dapat diakses lewat shortcut Desktop atau Start Menu.

## Privasi

Ubahin memproses file secara lokal di perangkat pengguna. Aplikasi tidak mengunggah dokumen ke server.

## Status Pengembangan

Ini adalah versi `0.1.1-beta`. Beberapa fitur utama sudah berjalan dengan stabil, seperti fungsi dasar konversi PDF ke JPG. Beberapa pembaruan antarmuka (GUI) dan fitur tambahan masih dalam tahap pengembangan aktif.

## Cara Melaporkan Bug

Bila Anda menemukan masalah atau error, silakan buat *Issue* di GitHub dengan cara:
1. Buka tab [Issues](https://github.com/Catalism-1/UbahIn/issues).
2. Klik **New Issue** dan pilih template **Bug Report**.
3. Isi informasi yang diperlukan sesuai dengan form yang muncul.


## Yang Ada Saat Ini

- CLI backend lama tetap tersedia melalui `ubahin.cli`.
- Self-check internal: `Ubahin.exe --self-check --silent`.
- Startup diagnostics ke `%LOCALAPPDATA%\Ubahin\logs\startup.log`.
- Data pengguna di `%LOCALAPPDATA%\Ubahin\`.
- Build debug console di `dist_debug\Ubahin\Ubahin.exe`.
- Build portable release di `dist\Ubahin\Ubahin.exe`.
- Installer Inno Setup di `dist\installer\Ubahin_Setup.exe`.
- Native Rust tetap opsional. Jika tidak ada, aplikasi memakai fallback Python.

## Struktur Penting

```text
main.py                         entry point desktop untuk EXE
src/ubahin/cli.py               CLI backend lama
src/ubahin/desktop/app.py       launcher desktop
src/ubahin/desktop/main_window.py window utama UI demo
src/ubahin/desktop/pages/       halaman PDF ke JPG, self-check, tentang
src/ubahin/desktop/widgets/     widget antrean file, setting, progress
src/ubahin/desktop/self_check.py self-check internal
src/ubahin/desktop/startup.py   startup diagnostics
src/ubahin/desktop/diagnostics.py diagnostic report
build_debug.bat                 build EXE console
build_portable.bat              build EXE release portable
build_installer.bat             build installer dan silent install test
diagnose_ubahin.bat             laporan kondisi sistem
run_dev.bat                     menjalankan desktop shell dari source
```

## Menjalankan dari Source

```bat
cd "D:\Projek Pribadi Kode\convert_pdf\Ubahin_backend_foundation\Ubahin"
build_portable.bat
run_dev.bat
```

`build_portable.bat` akan membuat `.venv` lokal bila belum ada dan menginstal dependency ke virtual environment tersebut.

Untuk menjalankan CLI backend lama:

```bat
set PYTHONPATH=%CD%\src
.venv\Scripts\python.exe -m ubahin.cli "C:\PDF\contoh.pdf" -o "C:\Hasil Ubahin" --preset high
```

## Self-Check

Dari source:

```bat
set PYTHONPATH=%CD%\src
.venv\Scripts\python.exe main.py --self-check --silent
```

Dari portable atau hasil install:

```bat
dist\Ubahin\Ubahin.exe --self-check --silent
```

Self-check memeriksa app data, folder log, SQLite history, PyMuPDF, Pillow, pypdf, dan status native module opsional.

## Menjalankan Test

```bat
run_tests.bat
```

Script ini menjalankan pytest dengan temporary folder lokal `.pytest_tmp` agar stabil di Windows dan tidak bergantung pada permission folder `%TEMP%`.

Perintah standar juga dapat dipakai:

```bat
python -m pytest
```

Konfigurasi pytest di `pyproject.toml` memakai `.pytest_tmp` sebagai base temp. Folder tersebut diabaikan Git dan aman dihapus setelah test selesai.

## Build Debug

```bat
build_debug.bat
```

Hasil:

```text
dist_debug\Ubahin\Ubahin.exe
```

Mode debug memakai console supaya error startup terlihat langsung.

## Build Portable

```bat
build_portable.bat
```

Hasil:

```text
dist\Ubahin\Ubahin.exe
dist\Ubahin\self_check_output.txt
```

Build dianggap gagal jika self-check portable gagal.

## Build Installer

Butuh Inno Setup 6.

```bat
build_installer.bat
```

Script ini akan:

- membangun portable release,
- membuat installer,
- silent install ke `%TEMP%\UbahinInstallTest`,
- menjalankan `Ubahin.exe --self-check --silent`,
- uninstall test installation.

Hasil:

```text
dist\installer\Ubahin_Setup.exe
```

Installer default ke:

```text
%LOCALAPPDATA%\Programs\Ubahin
```

## Diagnostic Report

```bat
diagnose_ubahin.bat
```

Output disimpan ke:

```text
%LOCALAPPDATA%\Ubahin\logs\diagnostic_report.txt
```

## Jika Aplikasi Gagal Dibuka atau Konversi Gagal

Cek log:

```text
%LOCALAPPDATA%\Ubahin\logs\startup.log
%LOCALAPPDATA%\Ubahin\logs\ubahin.log
%LOCALAPPDATA%\Ubahin\logs\self_check.log
%LOCALAPPDATA%\Ubahin\logs\diagnostic_report.txt
```

Jika dijalankan dari release `--noconsole`, aplikasi akan menampilkan dialog sederhana dan menyimpan traceback lengkap ke `startup.log`.

Jika error muncul saat klik `Mulai Ubah File`, cek `ubahin.log`. UI demo memakai event queue agar worker converter tidak menyentuh Tkinter langsung; log mencatat nama thread, jenis event, dan job id saat proses berjalan.

## Catatan

- GUI final Claude belum digabungkan.
- Rust/Cargo/Maturin bukan syarat build installer pertama.
- Native acceleration aktif hanya jika module `ubahin_native` tersedia dan lolos import.
- Semua proses aplikasi berjalan lokal/offline.
