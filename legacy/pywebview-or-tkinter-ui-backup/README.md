# Legacy UI (CustomTkinter / pywebview / PyInstaller)

Arsip entry point dan script build aplikasi desktop lama (sebelum migrasi ke Tauri 2 + React).
Dipindahkan ke sini pada persiapan rilis v0.1.2 agar root repo merepresentasikan aplikasi aktif
(Tauri 2 + React + Rust + Python sidecar), bukan generasi UI sebelumnya.

Isi folder ini:

- `main.py`, `desktop_main.py` — entry point PyInstaller aplikasi lama.
- `Ubahin.spec` — spec file PyInstaller.
- `installer_script.iss` — script Inno Setup installer lama.
- `build_debug.bat`, `build_portable.bat`, `build_installer.bat`, `build_release_assets.bat` — build script PyInstaller/Inno Setup.
- `run_dev.bat` — dev runner lama (menjalankan `main.py` langsung, bukan Tauri).
- `diagnose_ubahin.bat`, `test_installer_windows.bat` — diagnostic dan test installer lama.

Script-script ini mengasumsikan dijalankan dari root repo asli (bukan dari dalam folder ini) dan
sudah tidak dipelihara aktif. Untuk menjalankan/build aplikasi saat ini, lihat `README.md` di root
repo (alur Tauri 2 melalui `desktop-tauri/` dan `build_release_windows.bat`).

`src/ubahin/desktop/` (kode UI Tkinter lama) masih ada di lokasi aslinya dan belum dipindahkan pada
tahap ini.
