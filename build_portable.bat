@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "APP_NAME=Ubahin"
set "DIST_ROOT=dist"
set "DIST_PATH=%DIST_ROOT%\%APP_NAME%"
set "BUILD_LOG=%DIST_ROOT%\portable_build_output.txt"

call :prepare_python
if errorlevel 1 exit /b 1

if not exist "%DIST_ROOT%" mkdir "%DIST_ROOT%"
echo Building %APP_NAME% portable release... > "%BUILD_LOG%"

"%PYTHON_EXE%" -c "import fitz, PIL, pypdf, PyInstaller, webview" >nul 2>nul
if errorlevel 1 (
  echo Installing dependencies into local virtual environment...
  "%PYTHON_EXE%" -m pip install -r requirements.txt >> "%BUILD_LOG%" 2>&1
  if errorlevel 1 (
    echo Gagal install dependency. Lihat %BUILD_LOG%
    exit /b 1
  )
) else (
  echo Dependencies already available. >> "%BUILD_LOG%"
)

if exist build rmdir /s /q build
if exist "%DIST_PATH%" rmdir /s /q "%DIST_PATH%"
if exist Ubahin.spec del /q Ubahin.spec

set "ICON_ARGS="
if exist "assets\app_icon.ico" (
  set "ICON_ARGS=--icon assets\app_icon.ico"
) else (
  echo WARNING: assets\app_icon.ico tidak ditemukan. Build dilanjutkan tanpa icon.
)

set "DATA_ARGS="
if exist assets set "DATA_ARGS=--add-data assets;assets"
if exist "src\ubahin\desktop\web" set "DATA_ARGS=%DATA_ARGS% --add-data src\ubahin\desktop\web;ubahin\desktop\web"

set "NATIVE_ARGS="
"%PYTHON_EXE%" -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('ubahin_native') else 1)" >nul 2>nul
if not errorlevel 1 set "NATIVE_ARGS=--hidden-import ubahin_native"

"%PYTHON_EXE%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --noconsole ^
  --name "%APP_NAME%" ^
  --distpath "%DIST_ROOT%" ^
  --paths src ^
  %ICON_ARGS% ^
  %DATA_ARGS% ^
  --collect-all pymupdf ^
  --collect-all PIL ^
  --collect-all webview ^
  --hidden-import pypdf ^
  --hidden-import webview ^
  --hidden-import webview.platforms.winforms ^
  --hidden-import clr_loader ^
  --hidden-import pythonnet ^
  --hidden-import bottle ^
  --hidden-import proxy_tools ^
  %NATIVE_ARGS% ^
  --exclude-module pytest ^
  --exclude-module ruff ^
  --exclude-module maturin ^
  --exclude-module pandas ^
  --exclude-module openpyxl ^
  --exclude-module lxml ^
  main.py >> "%BUILD_LOG%" 2>&1
if errorlevel 1 (
  echo Build portable gagal. Lihat %BUILD_LOG%
  exit /b 1
)

if exist native\ubahin_native\target (
  if exist "%DIST_PATH%\_internal" (
    for /r native\ubahin_native\target %%F in (ubahin_native*.pyd) do copy "%%F" "%DIST_PATH%\_internal\" >nul
  )
)

if exist README.md copy README.md "%DIST_PATH%\README.md" >nul
if exist VERSION copy VERSION "%DIST_PATH%\VERSION" >nul
if exist CHANGELOG.md copy CHANGELOG.md "%DIST_PATH%\CHANGELOG.md" >nul

echo Running portable self-check...
"%DIST_PATH%\%APP_NAME%.exe" --self-check --silent > "%DIST_PATH%\self_check_output.txt" 2>&1
if errorlevel 1 (
  echo Portable self-check gagal.
  type "%DIST_PATH%\self_check_output.txt"
  exit /b 1
)

echo Portable build selesai: %DIST_PATH%\%APP_NAME%.exe
echo Self-check output: %DIST_PATH%\self_check_output.txt
exit /b 0

:prepare_python
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
  set "PYTHON_BOOTSTRAP=%PYTHON_CMD%"
  if "!PYTHON_BOOTSTRAP!"=="" (
    py -3.11 -V >nul 2>nul
    if not errorlevel 1 set "PYTHON_BOOTSTRAP=py -3.11"
  )
  if "!PYTHON_BOOTSTRAP!"=="" (
    py -V >nul 2>nul
    if not errorlevel 1 set "PYTHON_BOOTSTRAP=py"
  )
  if "!PYTHON_BOOTSTRAP!"=="" (
    python -V >nul 2>nul
    if not errorlevel 1 set "PYTHON_BOOTSTRAP=python"
  )
  if "!PYTHON_BOOTSTRAP!"=="" (
    echo Python 3.11+ tidak ditemukan.
    exit /b 1
  )
  !PYTHON_BOOTSTRAP! -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
  if errorlevel 1 (
    echo Python minimal 3.11 diperlukan.
    exit /b 1
  )
  echo Membuat virtual environment lokal .venv...
  !PYTHON_BOOTSTRAP! -m venv --system-site-packages .venv
  if errorlevel 1 (
    echo Gagal membuat .venv.
    exit /b 1
  )
  set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo Python di .venv harus versi 3.11+.
  exit /b 1
)
exit /b 0
