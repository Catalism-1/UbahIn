@echo off
setlocal
call build_portable.bat
if errorlevel 1 exit /b 1
where iscc >nul 2>nul
if errorlevel 1 (
  echo Inno Setup Compiler (iscc) belum ditemukan. Install Inno Setup lalu jalankan ulang.
  exit /b 1
)
iscc installer_script.iss
