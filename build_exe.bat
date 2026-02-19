@echo off
echo Building JoinSim.exe...
pip install pyinstaller
pyinstaller --onefile --windowed --name JoinSim --icon=icon.ico joinsim.py
echo.
echo Done! EXE is in dist/JoinSim.exe
pause
