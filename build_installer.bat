@echo off
setlocal EnableExtensions

call "%~dp0build_portable.bat"
if errorlevel 1 exit /b 1

set "ISCC_EXE="
where iscc >nul 2>nul
if not errorlevel 1 set "ISCC_EXE=iscc"
if "%ISCC_EXE%"=="" if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if "%ISCC_EXE%"=="" if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC_EXE%"=="" if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if "%ISCC_EXE%"=="" (
  echo Inno Setup 6 belum ditemukan. Instal terlebih dahulu, lalu jalankan ulang script ini.
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

echo Installer siap: dist\installer\Ubahin_Setup.exe
exit /b 0
