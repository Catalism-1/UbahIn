# UbahIn v0.1.3

UbahIn v0.1.3 adalah update untuk fitur Gambar ke PDF dan perbaikan konsistensi dark mode pada aplikasi desktop Windows berbasis Tauri 2.

## Highlight
- Gambar ke PDF kini mendukung hingga 100 gambar dalam satu antrean (naik dari batas sebelumnya).
- Batas 100 gambar disinkronkan di seluruh jalur validasi: UI React, engine (pemeriksaan file dan validasi start job), `JobManager`, dan `ImageToPdfService` — sehingga tidak ada lagi jalur yang diam-diam memotong daftar file atau membiarkan file lolos tanpa validasi.
- File ke-101 dan seterusnya ditolak dengan pesan error yang jelas ("Maksimal 100 gambar dalam satu antrean.") sebelum job dibuat.
- Perbaikan dark mode: hero banner, area upload, kartu, border, dan badge status error pada halaman Beranda, PDF ke JPG, Gambar ke PDF, Ubah Format Gambar, dan Gabungkan PDF tidak lagi memakai gradient/warna terang yang hardcode saat dark mode aktif, sehingga kontras teks dan elemen UI lebih konsisten.

## Verifikasi
- Python test suite: 72 test lulus, termasuk regression test baru yang membuktikan 100 gambar diterima dan menghasilkan PDF 100 halaman, serta 101 gambar ditolak dengan pesan error yang jelas di level service maupun engine.
- Frontend build: lulus (`npm ci` lalu `npm run build:frontend` -> `tsc`, `vite build`).
- Diff check: bersih.

## Catatan
Aplikasi memproses file secara lokal. Tidak ada upload dokumen ke server untuk fitur inti.
