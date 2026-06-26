# Ubahin

Ubahin adalah backend converter file lokal/offline untuk Windows. Release candidate lokal `0.1.1` fokus pada hal paling dasar untuk distribusi: aplikasi bisa di-build, diinstal, dibuka, dan diuji di laptop Windows 10/11 64-bit.

Tahap ini belum memasang GUI final Claude. `Ubahin.exe` sekarang membuka desktop shell sementara untuk validasi installer dan startup.

## Yang Ada Saat Ini

- Desktop launcher sementara berbasis Tkinter.
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
src/ubahin/desktop/app.py       desktop shell sementara
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

## Jika Aplikasi Gagal Dibuka

Cek log:

```text
%LOCALAPPDATA%\Ubahin\logs\startup.log
%LOCALAPPDATA%\Ubahin\logs\self_check.log
%LOCALAPPDATA%\Ubahin\logs\diagnostic_report.txt
```

Jika dijalankan dari release `--noconsole`, aplikasi akan menampilkan dialog sederhana dan menyimpan traceback lengkap ke `startup.log`.

## Catatan

- GUI final Claude belum digabungkan.
- Rust/Cargo/Maturin bukan syarat build installer pertama.
- Native acceleration aktif hanya jika module `ubahin_native` tersedia dan lolos import.
- Semua proses aplikasi berjalan lokal/offline.
