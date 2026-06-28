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
- Tahap 2C: Stabilisasi PDF ke JPG, pengenalan menu Diagnostik, perbaikan *graceful shutdown* sidecar, penambahan logging (termasuk `last_error.txt`), skrip build release otomatis `build_release_windows.bat`, dan skrip test instalasi `test_installer_windows.bat`.

Belum dikerjakan:

- Memindahkan desain/fungsi final untuk tool selain PDF ke JPG.
- Optimasi ukuran sidecar PyInstaller.

Selesai di Tahap 2D (lihat bagian "Tahap 2D" di bawah):

- Riwayat React penuh dari SQLite.
- Settings backend penuh untuk semua opsi.

## Tahap 2C: Stabilisasi, Diagnostik, dan Packaging Windows

Tahap ini berfokus pada membuat build release (installer) dari aplikasi Tauri yang bisa digunakan secara stand-alone di mesin pengguna Windows tanpa require node.js atau python terinstal.

Perubahan penting:
1. **Sidecar Error Handling & Graceful Shutdown**: `ubahin-engine.exe` kini menerima perintah `shutdown` untuk berhenti secara bersih, `stderr` di-redirect ke file log, dan `sidecar.rs` dalam Rust memastikan *sidecar* dimatikan secara benar ketika aplikasi ditutup. Error fatal dari Tauri kini disimpan di `last_error.txt`.
2. **Menu Diagnostik**: Halaman 'Pemeriksaan Engine' diubah menjadi halaman 'Diagnostik Sistem' yang menampilkan *app version*, lokasi instalasi, lokasi log, status berbagai fitur PyMuPDF, Pillow, pypdf, beserta tombol *Copy Diagnostic*.
3. **Build Release Windows**: Proses build otomatis Python + Tauri disatukan dalam skrip `build_release_windows.bat` yang akan meng-output installer `.exe` di dalam folder `src-tauri/target/release/bundle/nsis/`.
4. **Test Installer**: `test_installer_windows.bat` mensimulasikan instalasi di latar belakang (silent install), mengecek bahwa `ubahin-engine` dapat berjalan pada direktori target, kemudian melakukan *silent uninstall*.

### Skrip Build Release Windows

Gunakan perintah ini untuk membuat installer resmi:
```bat
build_release_windows.bat
```
Proses ini akan mengumpulkan semua dependensi Python, mem-build `ubahin-engine.exe`, menjalankan test, mengompilasi Vite (React) dengan perintah `npm run build:frontend`, lalu membungkus installer dengan `npm run tauri build`.

### Skrip Test Installer Windows

Gunakan perintah ini setelah build selesai untuk mengetes hasil instalasi:
```bat
test_installer_windows.bat
```
Skrip ini akan memeriksa *sidecar* dan *engine_version* dari hasil unpack *installer* `.exe` Tauri.

### Lokasi Log
Lokasi utama *app data* dan *log*:
- `%LOCALAPPDATA%\Ubahin\logs\tauri.log`: Log error dan aktivitas window Tauri.
- `%LOCALAPPDATA%\Ubahin\logs\engine.stderr.log`: Log native Python stderr dari sidecar.
- `%LOCALAPPDATA%\Ubahin\logs\last_error.txt`: Informasi ketika panic/error fatal terjadi.

**Troubleshooting jika Sidecar gagal dimuat:**
1. Cek `%LOCALAPPDATA%\Ubahin\logs\engine.stderr.log` untuk melihat apakah dependensi Python gagal dimuat.
2. Buka Menu **Diagnostik Sistem** dan cek status PyMuPDF, Pillow, pypdf, dan Native Accel.
3. Klik tombol *Cek Status Engine*. Jika macet, hapus folder `logs` dan reset *Window*.

Keterbatasan tahap 2B & 2C:
- Riwayat halaman React masih placeholder.
- Pengaturan global masih belum disimpan ke backend.
- Build sidecar onefile masih besar karena PyInstaller menarik dependency dari environment; ini target optimasi tahap berikutnya.

## Tahap 2D: Pengaturan & Riwayat Lokal Nyata

Tahap ini membuat halaman **Pengaturan** dan **Riwayat** menjadi fitur nyata yang tersimpan
secara lokal dan dapat dipakai ulang oleh semua converter berikutnya. Tidak ada perubahan pada
alur PDF ke JPG yang sudah stabil selain pembacaan default dari Pengaturan.

### Arsitektur persistence

```text
React UI
  → Tauri/Rust command (perantara aman, berbatas waktu)
  → Python sidecar (JSON Lines)
  → SQLite history + settings.json (di app data Ubahin)
```

Engine Python adalah **satu-satunya pemilik** database riwayat dan file pengaturan. React tidak
pernah menyentuh SQLite atau filesystem secara langsung; Rust hanya meneruskan request dan
membuka folder hasil bila diminta. Semua data tersimpan **lokal** — tidak ada cloud, API online,
atau sinkronisasi internet.

### Lokasi database dan settings

| Data | Lokasi |
| --- | --- |
| Pengaturan | `%LOCALAPPDATA%\Ubahin\settings\settings.json` |
| Riwayat (SQLite) | `%LOCALAPPDATA%\Ubahin\history\history.sqlite3` |
| Backup migrasi DB | `%LOCALAPPDATA%\Ubahin\history\history.sqlite3.v<versi>.bak` |

Tidak ada data yang disimpan di folder instalasi. Tidak ada data sensitif yang disimpan.

### Alur Pengaturan (settings flow)

- Action engine: `get_settings`, `save_settings`. Command Rust: `get_settings`, `save_settings`,
  `select_default_output_directory`.
- File disimpan dengan **schema + versi** dan ditulis **atomic** (tulis ke file sementara lalu
  `rename`) sehingga tidak pernah setengah tertulis.
- Seluruh enum dan angka **divalidasi**; nilai rusak atau hilang otomatis memakai default aman.
- Saat aplikasi dibuka React memuat settings dari engine. Tema langsung diterapkan saat diubah.
  `localStorage` hanya dipakai sebagai cache tema untuk paint awal / fallback bila engine belum
  tersedia — bukan sumber kebenaran.
- Field pengaturan: `theme`, `default_output_directory`, `performance_mode`, `default_pdf_preset`,
  `default_dpi`, `default_jpeg_quality`, `create_zip_after_conversion`, `open_output_after_finish`,
  `notifications_enabled`.

### Alur Riwayat (history flow)

- Action engine: `list_history`, `get_recent_history`, `delete_history_item`, `clear_history`,
  `open_history_output_directory`. Command Rust dengan nama sama (membuka folder lewat Rust).
- Setiap job menghasilkan **tepat satu** record. Job berstatus `completed`,
  `completed_with_warnings`, `failed`, atau `cancelled` semuanya tercatat dengan status yang tepat
  (penyimpanan dilakukan di blok `finally` `JobManager._run_job`).
- Beranda "Terakhir digunakan" memakai `get_recent_history(limit=5)`; halaman Riwayat memakai
  `list_history` dengan paginasi dan filter (Semua / Berhasil / Gagal / Dibatalkan). Filter
  "Berhasil" mencakup juga `completed_with_warnings`.

### Batas maksimal 500 record

Database menyimpan maksimal **500 record terbaru**. Saat melewati batas, hanya record **tertua**
yang dihapus (retention berjalan setiap kali record baru disimpan). Record lama pengguna tidak
pernah dihapus selama masih di dalam 500 terbaru.

### Privasi & keamanan data

- Semua riwayat dan pengaturan tersimpan **lokal** di `%LOCALAPPDATA%\Ubahin`.
- **Menghapus record riwayat tidak menghapus file hasil pengguna.** Hanya catatan di database yang
  dihapus; file JPG/ZIP tetap berada di foldernya.
- Bila folder hasil sudah tidak ada saat membuka dari Riwayat, aplikasi tidak crash dan menampilkan
  pesan `Folder hasil tidak ditemukan.`

### Migrasi schema SQLite

- Migrasi dilakukan **berurutan dan transaksional**. Database lama dibackup (`*.v<versi>.bak`)
  sebelum migrasi besar sehingga selalu dapat dipulihkan bila terjadi kegagalan.
- Migrasi v1 → v2 menambahkan kolom `created_at` dan `warning_count` tanpa merusak record lama;
  `created_at` diisi mundur dari `started_at`/`finished_at` untuk record yang sudah ada.

### Cara reset settings tanpa menghapus history

Hapus file `%LOCALAPPDATA%\Ubahin\settings\settings.json`. Saat aplikasi dibuka kembali, engine
mengembalikan default aman dan membuat ulang file tersebut. Database riwayat di folder `history`
tidak tersentuh.

### Cara clear history tanpa menghapus file hasil

Gunakan tombol **Hapus Riwayat** di halaman Riwayat (atau hapus file
`%LOCALAPPDATA%\Ubahin\history\history.sqlite3`). Tindakan ini hanya membersihkan catatan; semua
file hasil konversi di folder output pengguna tetap utuh.

## Tahap 3A: Gambar ke PDF (Image to PDF)

Tahap ini menambahkan converter kedua, yaitu **Gambar ke PDF**, yang menggabungkan banyak gambar (JPG, JPEG, PNG, WEBP) menjadi satu file PDF secara lokal, aman, dan responsif.

### Arsitektur Gambar ke PDF

```text
React UI (ImageToPdfPage)
  → pickImageFiles (Tauri command / rfd native picker)
  → inspectImageFiles (Tauri command → Python sidecar)
  → startImageToPdf (Tauri command → Python sidecar)
  → Python ImageToPdfService (PIL processing)
  → Event progress & completion disalurkan ke React
```

### Action JSON Lines Baru

1. **`inspect_image_files`**
   - Menganalisis metadata gambar (format, dimensi px, ukuran bytes) dan menghasilkan thumbnail base64 (sisi terpanjang maks 160px, transparansi disatukan dengan background putih untuk preview).
   - Payload: `{"paths": ["C:\\path\\foto.png"]}`
   - Response minimal: `{"file_id": "uuid", "path": "...", "filename": "...", "size_bytes": 123, "format": "PNG", "width": 800, "height": 600, "status": "ready", "thumbnail_data_uri": "data:image/jpeg;base64,..."}`

2. **`start_image_to_pdf`**
   - Menjalankan job penggabungan gambar menjadi PDF.
   - Payload:
     ```json
     {
       "job_id": "uuid",
       "files": [{"file_id": "uuid", "path": "C:\\path\\foto.png"}],
       "output_directory": "C:\\Hasil",
       "output_filename": "Dokumen.pdf",
       "page_size": "original",
       "orientation": "auto",
       "margin": "normal",
       "fit_mode": "contain",
       "open_output_after_finish": true,
       "performance_mode": "balanced"
     }
     ```

### Pengaturan & Opsi Gambar ke PDF

- **`page_size`**: `original` (dimensi asli gambar + margin), `a4`, `letter`.
- **`orientation`**: `auto` (menyesuaikan orientasi per gambar), `portrait`, `landscape`.
- **`margin`**: `none` (0 pt), `small` (18 pt), `normal` (36 pt).
- **`fit_mode`**: `contain` (gambar pas di dalam halaman), `fill` (gambar memenuhi halaman secara penuh dan dipotong sisanya secara presisi).

### Optimasi Memori & Kualitas

- **Sequential Processing**: Gambar masukan dibuka dan dibebaskan dari memori RAM satu per satu. Hanya objek *canvas* hasil render dengan dimensi cetak (seperti A4) yang dipertahankan dalam list memori untuk fungsi penulisan akhir `save(..., save_all=True)`. Hal ini mencegah pembengkakan memori akibat gambar resolusi tinggi (misal kamera 12MP+).
- **Transparency Blending**: Gambar PNG/WEBP transparan dipadukan secara otomatis di atas warna latar belakang putih polos agar file PDF tidak rusak.
- **EXIF Auto-Rotation**: Data orientasi EXIF kamera dikoreksi secara otomatis (`ImageOps.exif_transpose`) sebelum gambar dimasukkan ke PDF.
- **Atomic File Writing**: File ditulis ke file sementara (`.tmp`) lebih dulu, lalu di-rename setelah sukses. File sementara langsung dihapus jika proses gagal atau dibatalkan.
