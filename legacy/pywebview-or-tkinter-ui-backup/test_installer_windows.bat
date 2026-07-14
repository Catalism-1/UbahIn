@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo =======================================================
echo TEST INSTALLER WINDOWS TAURI - UBAHIN
echo =======================================================

cd /d "%~dp0"

set "INSTALLER_DIR=desktop-tauri\src-tauri\target\release\bundle\nsis"
if not exist "%INSTALLER_DIR%" (
    echo [ERROR] Folder installer tidak ditemukan: %INSTALLER_DIR%
    echo Harap jalankan build_release_windows.bat terlebih dahulu.
    exit /b 1
)

set "INSTALLER_PATH="
for %%I in ("%INSTALLER_DIR%\*.exe") do (
    set "INSTALLER_PATH=%%~fI"
)

if not defined INSTALLER_PATH (
    echo [ERROR] Installer exe tidak ditemukan di folder %INSTALLER_DIR%
    exit /b 1
)

echo [OK] Installer ditemukan: %INSTALLER_PATH%

set "TEST_DIR=%TEMP%\UbahinTestInstall"
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"

echo.
echo Melakukan silent install ke %TEST_DIR% ...
"%INSTALLER_PATH%" /S /D=%TEST_DIR%
if errorlevel 1 (
    echo [ERROR] Silent install gagal.
    exit /b 1
)

:: Tunggu sebentar untuk memastikan file tersalin
timeout /t 3 /nobreak >nul

if not exist "%TEST_DIR%\ubahin_desktop.exe" (
    if exist "%TEST_DIR%\Ubahin.exe" (
        set "APP_EXE=Ubahin.exe"
    ) else (
        echo [ERROR] Executable aplikasi tidak ditemukan di %TEST_DIR%.
        exit /b 1
    )
) else (
    set "APP_EXE=ubahin_desktop.exe"
)
echo [OK] Aplikasi terinstal di %TEST_DIR%\%APP_EXE%

echo.
echo Menguji Sidecar Engine secara langsung...
set "SIDECAR_EXE=%TEST_DIR%\ubahin-engine.exe"
if exist "%TEST_DIR%\binaries\ubahin-engine-x86_64-pc-windows-msvc.exe" (
    set "SIDECAR_EXE=%TEST_DIR%\binaries\ubahin-engine-x86_64-pc-windows-msvc.exe"
)

if not exist "%SIDECAR_EXE%" (
    echo [ERROR] Sidecar engine tidak ditemukan di lokasi instalasi.
    echo Cek struktur direktori di %TEST_DIR%
    dir "%TEST_DIR%"
    exit /b 1
)

:: Panggil engine self_check lewat command line test sederhana (simulasi payload health)
echo {"action":"health", "id":"test-123"} | "%SIDECAR_EXE%" --stdio > "%TEMP%\engine_test_output.txt"
findstr /i "engine_version" "%TEMP%\engine_test_output.txt" >nul
if errorlevel 1 (
    echo [ERROR] Sidecar engine gagal merespons dengan format yang benar.
    type "%TEMP%\engine_test_output.txt"
    exit /b 1
)
echo [OK] Sidecar engine berfungsi dengan baik.

echo.
echo Melakukan uninstall...
if exist "%TEST_DIR%\Uninstall Ubahin.exe" (
    "%TEST_DIR%\Uninstall Ubahin.exe" /S
) else if exist "%TEST_DIR%\uninst.exe" (
    "%TEST_DIR%\uninst.exe" /S
) else (
    echo [WARNING] Uninstaller tidak ditemukan. Menghapus folder secara manual.
    rmdir /s /q "%TEST_DIR%"
)

:: NSIS uninstaller berjalan async, tunggu sebentar sebelum foldernya benar-benar hilang
timeout /t 5 /nobreak >nul
if exist "%TEST_DIR%" (
    echo [WARNING] Menghapus sisa direktori instalasi test...
    rmdir /s /q "%TEST_DIR%"
)

echo.
echo =======================================================
echo TEST INSTALLER BERHASIL!
echo =======================================================
exit /b 0
