@echo off
setlocal EnableExtensions

rem Use a unique, writable folder outside the repo for pytest's basetemp.
rem Windows can leave the repo-local .pytest_tmp file-locked (Explorer preview,
rem antivirus, a lingering process), which then breaks every later run.
set "PYTEST_BASETEMP=%TEMP%\ubahin-pytest-%RANDOM%-%RANDOM%"
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

if not exist "%PYTEST_BASETEMP%" mkdir "%PYTEST_BASETEMP%"
"%PYTHON_EXE%" -m pytest --basetemp="%PYTEST_BASETEMP%" %*
set "TEST_EXIT=%ERRORLEVEL%"

rem Best-effort cleanup only; a locked/undeletable temp folder must never
rem change the test result, so its exit code is intentionally ignored.
if "%TEST_EXIT%"=="0" (
  rmdir /s /q "%PYTEST_BASETEMP%" >nul 2>nul
)

exit /b %TEST_EXIT%
