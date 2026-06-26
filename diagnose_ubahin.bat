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
  echo Python tidak ditemukan.
  exit /b 1
)

set "PYTHONPATH=%CD%\src"
"%PYTHON_EXE%" -m ubahin.desktop.diagnostics
if errorlevel 1 (
  echo Diagnostic gagal dijalankan.
  exit /b 1
)
