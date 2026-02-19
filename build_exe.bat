@echo off
echo ========================================
echo Building JoinSim.exe
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Install PyInstaller if needed
echo Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building with spec file (recommended)...
echo This creates a folder with all dependencies.
echo.

REM Use the spec file for proper building
pyinstaller joinsim.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed! Try running as Administrator.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Output: dist\JoinSim\JoinSim.exe
echo.
echo To distribute, zip the entire dist\JoinSim folder.
echo.
echo NOTE: Windows Defender may flag the .exe as unknown.
echo This is normal for PyInstaller apps. You can:
echo   1. Add an exclusion in Windows Security
echo   2. Submit to Microsoft for analysis (removes warning)
echo.
pause
