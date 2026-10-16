@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo   hide-face launcher
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found in PATH.
    echo Install Python 3.10 - 3.12 from https://www.python.org/downloads/
    echo During installation, check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
    echo.
)

echo Starting hide-face...
echo.
".venv\Scripts\python.exe" hide-face.py

echo.
echo hide-face has stopped.
pause