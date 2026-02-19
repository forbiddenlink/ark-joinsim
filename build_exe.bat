@echo off
echo Building JoinSim.exe...
pip install pyinstaller
if exist icon.ico (
    pyinstaller --onefile --windowed --name JoinSim --icon=icon.ico joinsim.py
) else (
    echo Note: icon.ico not found, building without custom icon
    pyinstaller --onefile --windowed --name JoinSim joinsim.py
)
echo.
echo Done! EXE is in dist/JoinSim.exe
pause
