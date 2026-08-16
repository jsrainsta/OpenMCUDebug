@echo off
rem ============================================================
rem  MCU Debug Assistant launcher
rem  Double-click this file to start (Windows)
rem
rem  Requirements:
rem    Python 3.10+ added to PATH
rem    Dependencies: python -m pip install -r requirements.txt
rem ============================================================
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

python -m desktop.main
if errorlevel 1 (
    echo.
    echo [ERROR] Launch failed. Install dependencies with:
    echo         python -m pip install -r requirements.txt
    pause
)