@echo off
setlocal
cd /d "%~dp0"

echo.
echo === Footage Workflow Setup ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/
    echo Check "Add python.exe to PATH" during install.
    exit /b 1
)

python --version

set "VENV_PY=.venv\Scripts\python.exe"
set "REBUILD=0"

if not exist "%VENV_PY%" (
    set "REBUILD=1"
) else (
    "%VENV_PY%" --version >nul 2>&1
    if errorlevel 1 set "REBUILD=1"
)

if "%REBUILD%"=="1" (
    if exist ".venv" (
        echo Removing old .venv - it was copied from another computer.
        rmdir /s /q ".venv"
    )
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 exit /b 1
)

echo Installing Python packages...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if not exist "config.yaml" (
    copy "config.example.yaml" "config.yaml"
    echo Created config.yaml - edit drive letters before first use.
) else (
    echo config.yaml already exists - skipped.
)

echo.
echo === Setup complete ===
echo.
echo Next steps:
echo   1. Edit config.yaml - set your drive letters
echo   2. Install rclone and run: rclone config
echo   3. .venv\Scripts\Activate.ps1
echo   4. python main.py list-scripts
echo.
endlocal
