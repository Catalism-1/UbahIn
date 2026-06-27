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

Response sukses tahap awal:

```json
{"type":"response","id":"request-1","ok":true,"data":{"engine_version":"0.1.1","python_available":true,"pymupdf_available":true,"pillow_available":true,"pypdf_available":true,"native_acceleration":"fallback","platform":"windows"}}
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
{"type":"response","id":"request-1","ok":true,"data":{}}
```

Response error:

```json
{"type":"response","id":"request-1","ok":false,"error":{"code":"ENGINE_ERROR","message":"Pesan sederhana berbahasa Indonesia"}}
```

Action tahap 1:

- `health`
- `app_info`
- `self_check`

Action tahap 2B:

- `inspect_pdf_files`
- `start_pdf_to_jpg`
- `cancel_job`
- `get_job_status`

Event engine tahap 2B:

```json
{"type":"event","event":"progress","job_id":"job-1","data":{"overall_percent":42}}
```

Event yang diteruskan Rust ke React:

- `engine://job-started`
- `engine://progress`
- `engine://file-completed`
- `engine://job-completed`
- `engine://job-failed`
- `engine://job-cancelled`
- `engine://warning`

## Status Tahap Migrasi

Sudah dibuat:

- Python engine sidecar mode `--stdio`.
- React + TypeScript shell sederhana.
- Rust command `check_engine`, `app_info`, `self_check`, dan `open_log_folder`.
- Timeout health check 10 detik.
- Logging error Tauri ke `%LOCALAPPDATA%\Ubahin\logs\tauri.log`.
- Tahap 2A app shell React dari arah visual desain Claude.
- Sidebar, topbar, theme manager, dan halaman placeholder modular.
- Halaman Pemeriksaan Engine dipindahkan ke komponen React modular tanpa mengubah command `check_engine`.
- Tahap 2B PDF ke JPG nyata dari React ke Python engine.
- Persistent sidecar manager di Rust dengan routing response per request ID dan forwarding event job ke React.
- Native file picker Rust untuk memilih PDF dan folder output.

Belum dikerjakan:

- Memindahkan desain/fungsi final untuk tool selain PDF ke JPG.
- Riwayat React penuh dari SQLite.
- Settings backend penuh untuk semua opsi.
- Optimasi ukuran sidecar PyInstaller.
- Validasi manual release di mesin pengguna akhir yang bersih.

## Tahap 2A: React App Shell

Tahap 2A memindahkan app shell visual dari referensi `design/reference/ubahin.html` ke React tanpa mengubah Python engine, Rust sidecar IPC, atau protocol JSON Lines.

Yang sudah dipindahkan:

- Identitas visual Ubahin dengan palet pastel Claude:
  `#F8F7F4`, `#FFFFFF`, `#DCD6F7`, `#CFE8D5`, `#D8E9F7`, `#F6D9C7`, `#7C9A7E`.
- Dark mode dengan background `#1E2220`, surface `#282E2B`, accent `#A8D5AE`.
- Sidebar menu: Beranda, Ubah PDF, Ubah Gambar, Riwayat, Pengaturan.
- Topbar dengan judul halaman aktif, status engine ringkas, dan tombol Pemeriksaan Engine.
- Responsive sidebar full di atas `1180px` dan compact/icon-only di bawahnya.
- Theme preference `light`, `dark`, dan `system` disimpan sementara lewat abstraction `localStorage`.
- Page shell untuk Beranda, Pemeriksaan Engine, Riwayat, Pengaturan, dan Coming Soon.

Placeholder tahap ini:

- PDF ke JPG masih berstatus `Segera disiapkan`.
- Gambar ke PDF, Gabungkan PDF, Kompres PDF, Ubah Ukuran Gambar, dan PDF ke Word masih `Segera hadir`.
- Riwayat belum membaca SQLite.
- Pengaturan belum menyimpan ke backend Python.
- Folder output default dan mode performa masih frontend-only.

Struktur React tahap 2A:

```text
desktop-tauri/src/
  components/AppShell/
  components/ThemeToggle/
  components/common/
  hooks/useTheme.ts
  pages/
  styles/
  types/navigation.ts
```

## Tahap 2B: PDF ke JPG Nyata

Tahap 2B membuat fitur PDF ke JPG pertama yang berjalan dari UI React sampai converter Python lokal. React tetap tidak mengakses filesystem langsung; path dipilih lewat command Rust, lalu Python engine memeriksa dan mengonversi file melalui JSON Lines stdin/stdout.

Alur:

1. React memanggil `pick_pdf_files`.
2. Rust membuka native PDF picker dan mengembalikan daftar path.
3. React memanggil `inspect_pdf_files`.
4. Python engine mengembalikan metadata file, jumlah halaman, dan error per file.
5. React memanggil `pick_output_directory`.
6. React memanggil `start_pdf_to_jpg` dengan `job_id`, file valid, output folder, preset, dan opsi.
7. Rust sidecar manager meneruskan event progress dari Python ke React.
8. React menampilkan progress, cancel, dan dialog hasil.

Command Tauri baru:

- `pick_pdf_files`
- `inspect_pdf_files`
- `pick_output_directory`
- `start_pdf_to_jpg`
- `cancel_pdf_to_jpg_job`
- `open_output_directory`
- `get_job_status`

Opsi preset PDF ke JPG:

- Standard: `150 DPI`, `JPG 80`
- Tinggi: `200 DPI`, `JPG 90`
- Sangat Tinggi: `300 DPI`, `JPG 95`

Test engine dari source:

```bat
cd Ubahin
echo {"id":"inspect-1","action":"inspect_pdf_files","payload":{"paths":["C:\\path\\file.pdf"]}} | .\.venv\Scripts\python.exe engine-python\engine_main.py --stdio
```

Build sidecar:

```bat
cd engine-python
build_engine.bat
```

Catatan: sidecar dibangun sebagai PyInstaller `--onefile` agar cocok dengan `externalBin` Tauri. Binary hasil build tetap tidak masuk Git.

Test UI:

```bat
cd desktop-tauri
npm run dev
```

Lalu buka `Ubah PDF`, jalankan `Pemeriksaan Engine`, pilih PDF, pilih folder output, dan klik `Mulai Ubah File`.

Keterbatasan tahap 2B:

- Riwayat halaman React masih placeholder.
- Pengaturan global masih belum disimpan ke backend.
- Gagal file per batch ditampilkan sebagai warning dan ringkasan hasil, belum menjadi halaman log terperinci di React.
- Build sidecar onefile masih besar karena PyInstaller menarik dependency dari environment; ini target optimasi tahap berikutnya.
