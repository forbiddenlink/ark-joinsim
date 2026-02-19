@echo off
echo Starting Ark JoinSim v4...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Run the application
python joinsim.py

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
