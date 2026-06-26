@echo off
setlocal

call build_portable.bat
if errorlevel 1 exit /b 1

set ISCC_EXE=
where iscc >nul 2>nul
if %errorlevel%==0 set ISCC_EXE=iscc
if "%ISCC_EXE%"=="" if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if "%ISCC_EXE%"=="" if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe
if "%ISCC_EXE%"=="" if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe

if "%ISCC_EXE%"=="" (
  echo Inno Setup Compiler tidak ditemukan. Install Inno Setup 6 lalu jalankan ulang.
  exit /b 1
)

"%ISCC_EXE%" installer_script.iss
