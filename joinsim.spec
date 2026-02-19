# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Ark JoinSim v4

Usage:
    pyinstaller joinsim.spec

This creates a standalone Windows executable with all dependencies.

Notes:
- Uses --onedir for faster startup (no extraction needed)
- Includes customtkinter data files for proper theming
- Excludes unnecessary packages to reduce size
"""

import sys
from pathlib import Path

# Get customtkinter path for data files
try:
    import customtkinter
    ctk_path = Path(customtkinter.__file__).parent
except ImportError:
    ctk_path = None
    print("WARNING: customtkinter not found - install it first")

block_cipher = None

# Data files to include
datas = [
    ('templates', 'templates'),  # Template images directory
]

# Add customtkinter theme files
if ctk_path:
    datas.append((str(ctk_path), 'customtkinter'))

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PIL._tkinter_finder',
    'cv2',
    'numpy',
    'mss',
    'keyboard',
    'pynput',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
]

# Add Windows-specific imports
if sys.platform == 'win32':
    hiddenimports.extend([
        'pydirectinput',
        'win32gui',
        'win32con',
        'win32api',
    ])

a = Analysis(
    ['joinsim.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
        'tkinter.test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JoinSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX to avoid antivirus false positives
    console=False,  # Hide console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='templates/icon.ico' if Path('templates/icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='JoinSim',
)
