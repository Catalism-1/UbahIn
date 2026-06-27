@echo off
setlocal EnableExtensions

set "PYTEST_BASETEMP=.pytest_tmp"
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

if not exist "%PYTEST_BASETEMP%" mkdir "%PYTEST_BASETEMP%"
"%PYTHON_EXE%" -m pytest --basetemp="%PYTEST_BASETEMP%" %*
set "TEST_EXIT=%ERRORLEVEL%"

if "%TEST_EXIT%"=="0" (
  rmdir /s /q "%PYTEST_BASETEMP%" >nul 2>nul
)

exit /b %TEST_EXIT%
