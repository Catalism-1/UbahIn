@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo =======================================================
echo BUILD RELEASE WINDOWS TAURI - UBAHIN TAHAP 2C
echo =======================================================

cd /d "%~dp0"

echo 1. Mengecek virtual environment Python...
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment tidak ditemukan di .venv
    echo Pastikan Anda telah menjalankan run_dev.bat atau membuat venv.
    exit /b 1
)
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

echo.
echo 2. Install dependency engine (jika diperlukan)...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal install dependencies Python.
    exit /b 1
)

echo.
echo 3. Build sidecar Python...
cd engine-python
call build_engine.bat
if errorlevel 1 (
    echo [ERROR] Gagal mem-build sidecar Python.
    exit /b 1
)
cd ..

echo.
echo 4. Verifikasi binary sidecar...
set "SIDECAR_EXE=desktop-tauri\src-tauri\binaries\ubahin-engine-x86_64-pc-windows-msvc.exe"
if not exist "%SIDECAR_EXE%" (
    echo [ERROR] Binary sidecar tidak ditemukan di %SIDECAR_EXE%
    exit /b 1
)
echo [OK] Binary sidecar tersedia.

echo.
echo 5. Jalankan test Python...
call run_tests.bat
if errorlevel 1 (
    echo [ERROR] Test Python gagal. Build dihentikan.
    exit /b 1
)

echo.
echo 6. Menjalankan frontend typecheck dan lint...
cd desktop-tauri
call npm install
if errorlevel 1 (
    echo [ERROR] Gagal install dependencies NPM.
    exit /b 1
)
call npm run build:frontend
if errorlevel 1 (
    echo [ERROR] Frontend build/typecheck gagal.
    exit /b 1
)

echo.
echo 7. Menjalankan Tauri Build...
call npm run tauri build
if errorlevel 1 (
    echo [ERROR] Tauri build gagal.
    exit /b 1
)

echo.
echo 8. Mencari installer hasil build...
set "INSTALLER_DIR=src-tauri\target\release\bundle\nsis"
if not exist "%INSTALLER_DIR%" (
    echo [ERROR] Folder installer tidak ditemukan: %INSTALLER_DIR%
    exit /b 1
)

for %%I in ("%INSTALLER_DIR%\*.exe") do (
    set "INSTALLER_PATH=%%~fI"
)

if not defined INSTALLER_PATH (
    echo [ERROR] Installer tidak ditemukan di folder %INSTALLER_DIR%
    exit /b 1
)

cd ..
echo =======================================================
echo BUILD BERHASIL!
echo Lokasi Installer:
echo %INSTALLER_PATH%
echo =======================================================
exit /b 0
