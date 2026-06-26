@echo off
setlocal EnableExtensions

call build_portable.bat
if errorlevel 1 exit /b 1

set "ISCC_EXE="
where iscc >nul 2>nul
if not errorlevel 1 set "ISCC_EXE=iscc"
if "%ISCC_EXE%"=="" if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if "%ISCC_EXE%"=="" if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC_EXE%"=="" if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if "%ISCC_EXE%"=="" (
  echo Inno Setup Compiler tidak ditemukan. Install Inno Setup 6 lalu jalankan ulang.
  exit /b 1
)

if not exist dist\installer mkdir dist\installer
"%ISCC_EXE%" installer_script.iss
if errorlevel 1 (
  echo Build installer gagal.
  exit /b 1
)

set "INSTALLER=%CD%\dist\installer\Ubahin_Setup.exe"
if not exist "%INSTALLER%" (
  echo Installer tidak ditemukan: %INSTALLER%
  exit /b 1
)

set "TEST_DIR=%TEMP%\UbahinInstallTest"
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"
mkdir "%TEST_DIR%"

echo Testing installer silent di %TEST_DIR%...
"%INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="%TEST_DIR%" /LOG="%TEST_DIR%\installer.log"
if errorlevel 1 (
  echo Silent install gagal. Log:
  if exist "%TEST_DIR%\installer.log" type "%TEST_DIR%\installer.log"
  exit /b 1
)

if not exist "%TEST_DIR%\Ubahin.exe" (
  echo Executable hasil instalasi tidak ditemukan.
  exit /b 1
)

"%TEST_DIR%\Ubahin.exe" --self-check --silent > "%TEST_DIR%\installer_self_check.txt" 2>&1
if errorlevel 1 (
  echo Self-check aplikasi terinstal gagal.
  type "%TEST_DIR%\installer_self_check.txt"
  if exist "%LOCALAPPDATA%\Ubahin\logs\startup.log" type "%LOCALAPPDATA%\Ubahin\logs\startup.log"
  exit /b 1
)

if exist "%TEST_DIR%\unins000.exe" (
  "%TEST_DIR%\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
)
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"

echo Installer build dan silent test selesai:
echo %INSTALLER%
exit /b 0
