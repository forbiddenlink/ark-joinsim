@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Ark JoinSim v4 - Windows Diagnostics
echo ========================================
echo.

:: Check Python
echo [1/8] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Install from python.org
    goto :error
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   OK: %%i
)

:: Check pip
echo.
echo [2/8] Checking pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: pip not found
    goto :error
) else (
    echo   OK: pip available
)

:: Check/Install dependencies
echo.
echo [3/8] Installing dependencies...
pip install -r requirements-windows.txt >nul 2>&1
if errorlevel 1 (
    echo   WARNING: Some dependencies may have failed
) else (
    echo   OK: Dependencies installed
)

:: Test core imports
echo.
echo [4/8] Testing Python imports...
python -c "import customtkinter; print('  OK: customtkinter')" 2>&1 || echo   FAIL: customtkinter
python -c "import cv2; print('  OK: opencv-python')" 2>&1 || echo   FAIL: opencv-python
python -c "import mss; print('  OK: mss')" 2>&1 || echo   FAIL: mss
python -c "import pyautogui; print('  OK: pyautogui')" 2>&1 || echo   FAIL: pyautogui
python -c "import keyboard; print('  OK: keyboard')" 2>&1 || echo   FAIL: keyboard
python -c "import pygetwindow; print('  OK: pygetwindow')" 2>&1 || echo   FAIL: pygetwindow

:: Test Windows-specific imports
echo.
echo [5/8] Testing Windows-specific modules...
python -c "import pydirectinput; print('  OK: pydirectinput')" 2>&1 || echo   WARN: pydirectinput (optional)
python -c "import dxcam; print('  OK: dxcam')" 2>&1 || echo   WARN: dxcam (optional)
python -c "import win32gui; print('  OK: pywin32')" 2>&1 || echo   WARN: pywin32 (optional)

:: Test screen capture
echo.
echo [6/8] Testing screen capture...
python -c "import mss; sct = mss.mss(); img = sct.grab(sct.monitors[1]); print(f'  OK: Screen captured {img.width}x{img.height}')" 2>&1

:: Test window detection
echo.
echo [7/8] Testing window detection...
python -c "import pygetwindow as gw; wins = gw.getAllTitles(); print(f'  OK: Found {len(wins)} windows')" 2>&1

:: Test tkinter
echo.
echo [8/8] Testing GUI (tkinter)...
python -c "import tkinter; root = tkinter.Tk(); root.withdraw(); root.destroy(); print('  OK: tkinter works')" 2>&1

echo.
echo ========================================
echo Diagnostics Complete
echo ========================================
echo.
echo If all tests passed, run: python joinsim.py
echo.
echo If tests failed, try:
echo   1. Run as Administrator
echo   2. pip install -r requirements-windows.txt
echo   3. Check antivirus isn't blocking Python
echo.
pause
goto :eof

:error
echo.
echo ========================================
echo SETUP FAILED - See errors above
echo ========================================
pause
