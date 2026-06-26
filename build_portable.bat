@echo off
setlocal

echo Building Ubahin portable...
if "%PYTHON_CMD%"=="" set "PYTHON_CMD=py"
%PYTHON_CMD% -V >nul 2>nul
if errorlevel 1 (
  set "PYTHON_CMD=python"
  python -V >nul 2>nul
)
%PYTHON_CMD% -V >nul 2>nul
if errorlevel 1 (
  echo Python tidak ditemukan. Install Python 3.11+ atau set PYTHON_CMD ke path python.exe.
  exit /b 1
)

%PYTHON_CMD% -m pip install -r requirements.txt

if exist native\ubahin_native\target (
  echo Native target folder found.
)

%PYTHON_CMD% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --noconsole ^
  --name Ubahin ^
  --paths src ^
  --icon "assets\app_icon.ico" ^
  --add-data "assets:assets" ^
  --collect-all pymupdf ^
  --collect-all PIL ^
  --hidden-import pypdf ^
  --hidden-import ubahin_native ^
  --exclude-module pytest ^
  --exclude-module ruff ^
  --exclude-module maturin ^
  --exclude-module pandas ^
  --exclude-module openpyxl ^
  --exclude-module lxml ^
  main.py
if errorlevel 1 (
  echo Build gagal.
  exit /b 1
)

if not exist dist\Ubahin\native mkdir dist\Ubahin\native
if exist native\ubahin_native\target\x86_64-pc-windows-msvc\release\*.pyd copy native\ubahin_native\target\x86_64-pc-windows-msvc\release\*.pyd dist\Ubahin\native\ >nul
copy README.md dist\Ubahin\README.md >nul
copy VERSION dist\Ubahin\VERSION >nul
copy CHANGELOG.md dist\Ubahin\CHANGELOG.md >nul
echo Portable build selesai: dist\Ubahin\Ubahin.exe
