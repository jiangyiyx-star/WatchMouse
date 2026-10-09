@echo off
cd /d "%~dp0"
if exist "dist\WatchMouse.exe" (
    start "" "dist\WatchMouse.exe"
    exit /b 0
)
if exist ".build-venv\Scripts\pythonw.exe" (
    start "" ".build-venv\Scripts\pythonw.exe" "app.py"
    exit /b 0
)
py -3 app.py
if errorlevel 1 (
    echo.
    echo Please install Python 3.10 or newer, then run build.ps1.
    pause
)
