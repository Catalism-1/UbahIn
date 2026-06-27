# Migrasi Tauri React

Dokumen ini mencatat tahap awal migrasi Ubahin dari shell Python desktop menuju arsitektur jangka panjang:

- Tauri 2 untuk window desktop, IPC, permission, sidecar, dan installer.
- React + TypeScript untuk GUI.
- Python untuk engine converter PDF/gambar yang sudah ada.
- Rust untuk command aman, window management, dan integrasi sistem.

Tahap ini belum memindahkan desain Claude dan belum memindahkan UI converter PDF ke JPG. Fokusnya hanya proof of architecture bahwa Tauri dapat memanggil Python engine lokal sebagai sidecar.

## Arsitektur Tahap 1

```text
React UI
  -> Tauri invoke("check_engine")
  -> Rust command
  -> Python sidecar ubahin-engine.exe --stdio
  -> JSON Lines stdin/stdout
  -> React menampilkan status
```

Komunikasi engine tidak memakai HTTP server, browser eksternal, localhost, atau pywebview. Tauri dev mode tetap memakai Vite untuk menyajikan UI selama development, tetapi IPC engine berjalan lewat stdin/stdout.

## Struktur Baru

```text
engine-python/
  engine_main.py
  requirements.txt
  build_engine.bat

desktop-tauri/
  src/
    App.tsx
    main.tsx
    services/engine.ts
    types/engine.ts
  src-tauri/
    src/main.rs
    src/commands.rs
    src/sidecar.rs
    binaries/
    tauri.conf.json
```

Source Python lama tetap berada di folder `src/ubahin` dan tidak dipindahkan.

## Menjalankan Python Engine

```bat
cd engine-python
echo {"id":"request-1","action":"health"} | ..\.venv\Scripts\python.exe engine_main.py --stdio
```

Response sukses:

```json
{"id":"request-1","ok":true,"data":{"engine_version":"0.1.1","python_available":true,"pymupdf_available":true,"pillow_available":true,"pypdf_available":true,"native_acceleration":"fallback","platform":"windows"}}
```

## Build Engine Sidecar

```bat
cd engine-python
build_engine.bat
```

Script ini membangun `ubahin-engine.exe` dengan PyInstaller dan menyalin binary ke:

```text
desktop-tauri\src-tauri\binaries\ubahin-engine-x86_64-pc-windows-msvc.exe
```

Binary tersebut tidak masuk Git.

## Menjalankan Tauri Dev

Prasyarat:

- Node.js dan npm.
- Rust toolchain dengan `cargo`.
- WebView2 Runtime di Windows.
- Sidecar sudah dibangun dengan `engine-python\build_engine.bat`.

```bat
cd desktop-tauri
npm install
npm run dev
```

Klik tombol `Cek Engine` pada halaman `Pemeriksaan Engine`.

## Build Tauri

```bat
cd desktop-tauri
npm install
npm run build
```

Hasil installer Tauri berada di folder target Tauri setelah build selesai.

## Window Behavior

Window utama memakai title bar native Windows, bukan custom title bar. Konfigurasi tahap ini:

- Label window: `main`
- Title: `Ubahin`
- Default size: `1440x900`
- Minimum size: `1100x700`
- Resizable: aktif
- Minimize, maximize, restore, close: aktif
- Decorations: aktif, agar Windows Snap Layout tetap tersedia
- Startup visibility: `false`, lalu window ditampilkan setelah restore state

Tidak ada `maxWidth` atau `maxHeight`, sehingga window tetap bisa diperbesar mengikuti monitor pengguna.

## Persistent Window State

Tauri memakai plugin resmi `tauri-plugin-window-state` untuk menyimpan dan memulihkan:

- ukuran window terakhir,
- posisi window terakhir,
- status maximize.

Saat startup, aplikasi mencoba restore state lebih dulu. Jika restore gagal, window memakai fallback `1440x900` dan diposisikan ke tengah layar. Error restore ditulis ke:

```text
%LOCALAPPDATA%\Ubahin\logs\tauri.log
```

## Reset Window State

Jika layout window tersimpan rusak, reset hanya state window dari app data Tauri/Ubahin. Jangan hapus folder settings, history, database, atau log engine kecuali memang dibutuhkan.

Langkah aman:

1. Tutup Ubahin.
2. Buka folder app data Ubahin di `%APPDATA%`, `%LOCALAPPDATA%`, atau folder data Tauri sesuai hasil build.
3. Hapus file state yang terkait window, biasanya bernama seperti `window-state.json` atau berada di folder data aplikasi Tauri.
4. Jalankan Ubahin lagi.

Aplikasi akan kembali memakai fallback `1440x900` di tengah layar bila state tidak ditemukan atau tidak valid.

## Protocol JSON Lines

Setiap request adalah satu JSON object per baris:

```json
{"id":"request-1","action":"health"}
```

Response sukses:

```json
{"id":"request-1","ok":true,"data":{}}
```

Response error:

```json
{"id":"request-1","ok":false,"error":{"code":"ENGINE_ERROR","message":"Pesan sederhana berbahasa Indonesia"}}
```

Action tahap 1:

- `health`
- `app_info`
- `self_check`

## Status Tahap Migrasi

Sudah dibuat:

- Python engine sidecar mode `--stdio`.
- React + TypeScript shell sederhana.
- Rust command `check_engine`, `app_info`, `self_check`, dan `open_log_folder`.
- Timeout health check 10 detik.
- Logging error Tauri ke `%LOCALAPPDATA%\Ubahin\logs\tauri.log`.

Belum dikerjakan:

- Memindahkan desain Claude.
- Memindahkan halaman PDF ke JPG ke React.
- Command `start_pdf_to_jpg`.
- Progress conversion dari Python ke React.
- Packaging final yang sudah divalidasi penuh di mesin release.
