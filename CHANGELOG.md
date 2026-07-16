# Changelog

## 0.1.3

### Added
- Gambar ke PDF kini mendukung hingga 100 gambar dalam satu antrean (naik dari batas sebelumnya).

### Fixed
- Batas 100 gambar disinkronkan di seluruh jalur validasi: UI React, engine (pemeriksaan file dan validasi start job), `JobManager`, dan `ImageToPdfService`, sehingga tidak ada lagi jalur yang diam-diam memotong daftar file atau membiarkan file lolos tanpa validasi.
- File ke-101 dan seterusnya ditolak dengan pesan error yang jelas ("Maksimal 100 gambar dalam satu antrean.") sebelum job dibuat.
- Dark mode: hero banner, area upload, kartu, border, dan badge status error pada halaman Beranda, PDF ke JPG, Gambar ke PDF, Ubah Format Gambar, dan Gabungkan PDF tidak lagi memakai gradient/warna terang yang hardcode saat dark mode aktif, sehingga kontras teks dan elemen UI lebih konsisten.

### Improved
- Regression test baru membuktikan 100 gambar diterima dan menghasilkan PDF 100 halaman, serta 101 gambar ditolak dengan pesan error yang jelas di level service maupun engine.

## 0.1.2

### Added
- Migrasi arsitektur desktop ke Tauri 2 + React + TypeScript, dengan Python sebagai sidecar engine (protokol JSON Lines via stdio).
- Fitur PDF ke JPG, Gambar ke PDF (termasuk HEIC), Ubah Format Gambar, dan Gabungkan PDF end-to-end.
- Riwayat (history) dan Pengaturan (settings) lokal terhubung penuh ke UI React.
- Diagnostik engine dan auto-check sidecar saat aplikasi dibuka.
- Dark mode dan layout desktop yang responsif di berbagai ukuran window.
- Script otomasi bump versi rilis (`scripts/bump_version.py`).

### Fixed
- Event completion job (PDF ke JPG, Gambar ke PDF) agar tidak race condition dan hanya tampil sukses setelah output benar-benar terverifikasi.
- Lifecycle sidecar Python agar berhenti dan pulih dengan andal, termasuk saat aplikasi ditutup.
- Beberapa perbaikan CI Windows untuk stabilitas build otomatis.

### Improved
- README dan dokumentasi (`docs/TAURI_MIGRATION.md`) diperbarui untuk mencerminkan arsitektur Tauri 2.
- Struktur repo dirapikan: entry point dan script build aplikasi generasi lama (CustomTkinter/pywebview/PyInstaller) diarsipkan ke `legacy/pywebview-or-tkinter-ui-backup/`.
- CI: workflow build/release lama tidak lagi otomatis terpicu oleh tag versi, mencegah rilis salah target (binary lama terpasang ke rilis Tauri).

## 0.1.1

- Mengubah entry point Windows menjadi launcher desktop sementara.
- Menambahkan self-check internal untuk portable dan installer.
- Menambahkan startup diagnostics ke `%LOCALAPPDATA%\Ubahin\logs\startup.log`.
- Menstabilkan build debug, build portable, installer silent-test, dan diagnostic report.
- Menjaga native Rust tetap opsional dengan fallback Python.

## 0.2.0

- Menambahkan resource governor adaptif untuk menjaga stabilitas CPU, RAM, dan disk.
- Menambahkan native bridge dengan fallback Python.
- Memperkeras lifecycle job, error code, logging, dan atomic write.
- Menambahkan workflow CI dan build Windows.

## 0.1.0

- Fondasi backend Ubahin: PDF ke JPG, service PDF/gambar, history, settings, dan test awal.
