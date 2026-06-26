# Changelog

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
