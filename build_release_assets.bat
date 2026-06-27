@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "RELEASE_DIR=dist\release"
set "PORTABLE_DIR=dist\Ubahin"
set "INSTALLER_EXE=dist\installer\Ubahin_Setup.exe"
set "PORTABLE_ZIP=%RELEASE_DIR%\Ubahin_Portable_Windows_x64.zip"
set "CHECKSUM_FILE=%RELEASE_DIR%\SHA256SUMS.txt"

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

echo Membangun portable release...
call "%~dp0build_portable.bat"
if errorlevel 1 (
    echo Gagal membangun portable release.
    exit /b 1
)

echo Membangun installer release...
call "%~dp0build_installer.bat"
if errorlevel 1 (
    echo Gagal membangun installer release.
    exit /b 1
)

echo Menjalankan self-check portable...
"%PORTABLE_DIR%\Ubahin.exe" --self-check --silent
if errorlevel 1 (
    echo Portable self-check gagal!
    exit /b 1
)

echo Menjalankan self-check installer...
set "TEST_DIR=%TEMP%\UbahinReleaseTest"
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"
"%INSTALLER_EXE%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="%TEST_DIR%"
"%TEST_DIR%\Ubahin.exe" --self-check --silent
if errorlevel 1 (
    echo Installer self-check gagal!
    exit /b 1
)
if exist "%TEST_DIR%\unins000.exe" "%TEST_DIR%\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"

echo Mempersiapkan aset portable...
echo Ubahin v0.1.1-beta> "%PORTABLE_DIR%\README_SINGKAT.txt"
echo.>> "%PORTABLE_DIR%\README_SINGKAT.txt"
echo Jalankan Ubahin.exe untuk menggunakan aplikasi.>> "%PORTABLE_DIR%\README_SINGKAT.txt"

echo Membuat ZIP portable...
if exist "%PORTABLE_ZIP%" del /q "%PORTABLE_ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path '%PORTABLE_DIR%\*' -DestinationPath '%PORTABLE_ZIP%' -Force"
if errorlevel 1 (
    echo Gagal membuat ZIP portable.
    exit /b 1
)

echo Mengcopy installer ke release dir...
copy "%INSTALLER_EXE%" "%RELEASE_DIR%\Ubahin_Setup.exe" /Y

echo Membuat file checksum...
if exist "%CHECKSUM_FILE%" del /q "%CHECKSUM_FILE%"
powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -Path '%RELEASE_DIR%\Ubahin_Setup.exe').Hash.ToLower() + '  Ubahin_Setup.exe' | Out-File -FilePath '%CHECKSUM_FILE%' -Encoding ascii -Append"
powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -Path '%PORTABLE_ZIP%').Hash.ToLower() + '  Ubahin_Portable_Windows_x64.zip' | Out-File -FilePath '%CHECKSUM_FILE%' -Encoding ascii -Append"

echo Selesai! Aset rilis tersedia di folder %RELEASE_DIR%:
dir /b "%RELEASE_DIR%"
exit /b 0
