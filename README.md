# UBAHIN

**Ubah file jadi lebih mudah.**

Ubahin adalah backend lokal/offline untuk aplikasi converter file Windows. Tahap ini fokus pada arsitektur backend, service layer, job system, validasi, riwayat SQLite, settings lokal, logging, dan API internal yang siap disambungkan ke GUI modern.

## Arsitektur

```text
src/ubahin/
├── core/
├── services/
├── utils/
└── ui_bridge/
```

Modul lama seperti `manager.py`, `converter.py`, `history.py`, dan `settings.py` tetap dipertahankan agar kode PDF ke JPG yang sudah bekerja tidak rusak.

## Fitur yang Sudah Jadi

- PDF ke JPG, maksimal 50 PDF per antrean.
- Render halaman PDF satu per satu dengan PyMuPDF.
- DPI: 120, 150, 200, 300.
- Kualitas JPG: 70, 80, 90, 95.
- Output per PDF masuk folder sendiri.
- Nama file aman Windows dan anti-tertimpa dengan suffix `_01`, `_02`.
- Progress per file, per halaman, dan keseluruhan.
- Pembatalan proses melalui cancellation token.
- Jika satu file gagal, file berikutnya tetap diproses.
- JPG/PNG/WEBP ke PDF.
- Merge PDF.
- Split PDF semua halaman atau rentang seperti `1-3, 4-8`.
- Kompres PDF lokal dengan PyMuPDF.
- Ubah format gambar.
- Resize gambar.
- Kompres gambar.
- ZIP hasil.
- Riwayat lokal SQLite.
- Settings lokal.
- Rotating log di `logs/ubahin.log`.
- UI bridge yang mengembalikan dictionary sederhana untuk GUI.

## Fitur Coming Soon

Fitur berikut sengaja tidak dibuat palsu:

- PDF ke Word dengan layout sempurna.
- Word ke PDF kompleks.
- OCR.
- Excel atau PowerPoint converter.

## Instalasi Dependency

```bat
cd "D:\Projek Pribadi Kode\convert_pdf\Ubahin_backend_foundation\Ubahin"
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

## Menjalankan Test

```bat
py -m pytest
```

## Menjalankan CLI Dummy

```bat
py main.py "C:\PDF\contoh.pdf" -o "C:\Hasil Ubahin" --preset high --zip
```

## Contoh API Internal

```python
from ubahin.core import JobManager

manager = JobManager()
job = manager.create_job(
    "pdf_to_jpg",
    [r"C:\PDF\contoh.pdf"],
    r"C:\Hasil Ubahin",
    dpi=200,
    jpg_quality=90,
)
manager.start_job(job.job_id)
manager.wait(job.job_id)
print(manager.get_job(job.job_id).to_dict())
```

## UI Bridge

```python
from ubahin.ui_bridge import AppController

controller = AppController()
response = controller.create_job(
    "merge_pdf",
    ["a.pdf", "b.pdf"],
    "hasil",
    output_name="gabungan.pdf",
)
controller.start_job(response["job_id"])
```

## Build Portable

```bat
build_portable.bat
```

Hasil:

```text
dist\Ubahin\Ubahin.exe
```

## Build Installer

Butuh Inno Setup 6.

```bat
build_installer.bat
```

Hasil:

```text
dist\installer\Ubahin_Setup.exe
```

## Catatan Keterbatasan

- Kompres PDF menggunakan optimasi aman dari PyMuPDF. Jika ukuran hasil tidak lebih kecil, sistem tidak mengklaim berhasil menghemat ukuran.
- PDF ke Word, Word ke PDF, dan OCR belum diimplementasikan karena membutuhkan pendekatan yang lebih khusus agar hasilnya tidak menyesatkan pengguna.
