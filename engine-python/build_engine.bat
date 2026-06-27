@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ENGINE_NAME=ubahin-engine"
set "TAURI_TRIPLE=x86_64-pc-windows-msvc"
set "PYTHON_EXE="

if exist "..\.venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\..\.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%ENGINE_NAME%.spec" del /q "%ENGINE_NAME%.spec"

"%PYTHON_EXE%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name "%ENGINE_NAME%" ^
  --paths ..\src ^
  --collect-all pymupdf ^
  --collect-all PIL ^
  --hidden-import pypdf ^
  engine_main.py
if errorlevel 1 exit /b 1

set "EXE_PATH=%CD%\dist\%ENGINE_NAME%.exe"
if not exist "%EXE_PATH%" (
  echo Engine executable tidak ditemukan: %EXE_PATH%
  exit /b 1
)

if not exist "..\desktop-tauri\src-tauri\binaries" mkdir "..\desktop-tauri\src-tauri\binaries"
copy /y "%EXE_PATH%" "..\desktop-tauri\src-tauri\binaries\%ENGINE_NAME%-%TAURI_TRIPLE%.exe" >nul
if errorlevel 1 exit /b 1

echo Engine sidecar selesai:
echo %EXE_PATH%
echo Disalin ke desktop-tauri\src-tauri\binaries\%ENGINE_NAME%-%TAURI_TRIPLE%.exe
