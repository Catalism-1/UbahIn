@echo off
setlocal EnableExtensions

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if "%PYTHON_EXE%"=="" (
  py -V >nul 2>nul
  if not errorlevel 1 set "PYTHON_EXE=py"
)
if "%PYTHON_EXE%"=="" (
  python -V >nul 2>nul
  if not errorlevel 1 set "PYTHON_EXE=python"
)
if "%PYTHON_EXE%"=="" (
  echo Python tidak ditemukan. Jalankan build_portable.bat untuk membuat .venv atau install Python 3.11+.
  exit /b 1
)

set "PYTHONPATH=%CD%\src"
"%PYTHON_EXE%" -c "import fitz, PIL, pypdf" >nul 2>nul
if errorlevel 1 (
  echo Dependency belum lengkap. Jalankan:
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo atau jalankan build_portable.bat untuk menyiapkan .venv otomatis.
  exit /b 1
)

"%PYTHON_EXE%" main.py
