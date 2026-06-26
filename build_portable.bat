@echo off
setlocal

echo Building Ubahin portable...
py -m pip install -r requirements.txt
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --console ^
  --name Ubahin ^
  --paths src ^
  --collect-all pymupdf ^
  --hidden-import pypdf ^
  main.py
if errorlevel 1 (
  echo Build gagal.
  exit /b 1
)

copy README.md dist\Ubahin\README.md >nul
echo Portable build selesai: dist\Ubahin\Ubahin.exe
REM Saat GUI final sudah diterapkan, ganti --console menjadi --windowed.
