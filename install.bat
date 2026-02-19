@echo off
echo ========================================
echo Ark JoinSim v4 - Windows Installer
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo Installing dependencies...
echo.

REM Install Windows-specific requirements
pip install -r requirements-windows.txt

if errorlevel 1 (
    echo.
    echo ERROR: Some dependencies failed to install.
    echo Try running this script as Administrator.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo To run JoinSim:
echo   python joinsim.py
echo.
echo Or double-click run.bat
echo.
pause
