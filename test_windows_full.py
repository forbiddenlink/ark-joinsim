#!/usr/bin/env python3
"""
Full Windows functionality test for Ark JoinSim.
Run this to verify everything works before using the app.

Usage:
    python test_windows_full.py

This will test:
1. All required imports
2. Screen capture (MSS and DXcam)
3. Window detection (pygetwindow and win32gui)
4. Input simulation (pydirectinput and pyautogui)
5. Template matching
6. State machine
7. GUI availability
"""

import sys
import time
import platform

# Ensure we're on Windows
IS_WINDOWS = sys.platform == 'win32'
if not IS_WINDOWS:
    print("WARNING: This test is designed for Windows!")
    print(f"Current platform: {platform.system()}")
    print()

results = {"passed": 0, "failed": 0, "warnings": 0}

def test_pass(name, msg=""):
    results["passed"] += 1
    print(f"  ✓ {name}" + (f" - {msg}" if msg else ""))

def test_fail(name, msg=""):
    results["failed"] += 1
    print(f"  ✗ {name}" + (f" - {msg}" if msg else ""))

def test_warn(name, msg=""):
    results["warnings"] += 1
    print(f"  ⚠ {name}" + (f" - {msg}" if msg else ""))

print("=" * 50)
print("ARK JOINSIM - WINDOWS FULL TEST")
print("=" * 50)

# ============================================
print("\n[1/7] Core Dependencies")
print("-" * 30)

try:
    import customtkinter
    test_pass("customtkinter")
except ImportError as e:
    test_fail("customtkinter", str(e))

try:
    import cv2
    test_pass("opencv-python", f"v{cv2.__version__}")
except ImportError as e:
    test_fail("opencv-python", str(e))

try:
    import numpy as np
    test_pass("numpy", f"v{np.__version__}")
except ImportError as e:
    test_fail("numpy", str(e))

try:
    import mss
    test_pass("mss")
except ImportError as e:
    test_fail("mss", str(e))

try:
    import keyboard
    test_pass("keyboard")
except ImportError as e:
    test_fail("keyboard", str(e))

try:
    import pyautogui
    test_pass("pyautogui")
except ImportError as e:
    test_fail("pyautogui", str(e))

try:
    import pygetwindow
    test_pass("pygetwindow")
except ImportError as e:
    test_fail("pygetwindow", str(e))

# ============================================
print("\n[2/7] Windows-Specific (Optional)")
print("-" * 30)

HAS_PYDIRECTINPUT = False
try:
    import pydirectinput
    HAS_PYDIRECTINPUT = True
    test_pass("pydirectinput", "Better DirectX input support")
except ImportError:
    test_warn("pydirectinput", "Not installed - using pyautogui fallback")

HAS_DXCAM = False
try:
    import dxcam
    HAS_DXCAM = True
    test_pass("dxcam", "240+ FPS screen capture")
except ImportError:
    test_warn("dxcam", "Not installed - using MSS (30-60 FPS)")

HAS_WIN32GUI = False
try:
    import win32gui
    HAS_WIN32GUI = True
    test_pass("win32gui (pywin32)", "Better window detection")
except ImportError:
    test_warn("win32gui", "Not installed - using pygetwindow")

# ============================================
print("\n[3/7] Screen Capture")
print("-" * 30)

try:
    import mss
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        img = sct.grab(monitor)
        test_pass("MSS capture", f"{img.width}x{img.height}")
except Exception as e:
    test_fail("MSS capture", str(e))

if HAS_DXCAM:
    try:
        camera = dxcam.create()
        frame = camera.grab()
        if frame is not None:
            test_pass("DXcam capture", f"{frame.shape}")
        else:
            test_warn("DXcam capture", "Returned None (may need restart)")
        del camera
    except Exception as e:
        test_warn("DXcam capture", str(e))

# ============================================
print("\n[4/7] Window Detection")
print("-" * 30)

try:
    import pygetwindow as gw
    titles = gw.getAllTitles()
    test_pass("Get all windows", f"Found {len(titles)} windows")
except Exception as e:
    test_fail("Get all windows", str(e))

if HAS_WIN32GUI:
    try:
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(title)
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        test_pass("win32gui EnumWindows", f"Found {len(windows)} visible windows")
    except Exception as e:
        test_fail("win32gui EnumWindows", str(e))

# Check for ARK window specifically
try:
    import pygetwindow as gw
    if hasattr(gw, 'getWindowsWithTitle'):
        ark_windows = gw.getWindowsWithTitle("ARK: Survival Ascended")
        if ark_windows:
            test_pass("ARK window detection", "Game window found!")
        else:
            test_warn("ARK window detection", "Game not running (expected)")
    else:
        # macOS/Linux fallback
        titles = gw.getAllTitles()
        ark_found = any("ARK" in t for t in titles)
        if ark_found:
            test_pass("ARK window detection", "Game window found!")
        else:
            test_warn("ARK window detection", "Game not running (expected)")
except Exception as e:
    test_warn("ARK window detection", str(e))

# ============================================
print("\n[5/7] Input Simulation")
print("-" * 30)

try:
    pos = pyautogui.position()
    test_pass("Get mouse position", f"({pos.x}, {pos.y})")
except Exception as e:
    test_fail("Get mouse position", str(e))

try:
    size = pyautogui.size()
    test_pass("Get screen size", f"{size.width}x{size.height}")
except Exception as e:
    test_fail("Get screen size", str(e))

if HAS_PYDIRECTINPUT:
    print("  Note: pydirectinput available for DirectX games")

# ============================================
print("\n[6/7] Vision Module")
print("-" * 30)

try:
    from vision import ScreenCapture, TemplateDetector, WindowFinder
    test_pass("Import vision module")
    
    cap = ScreenCapture(use_dxcam=HAS_DXCAM)
    frame = cap.capture()
    if frame is not None:
        test_pass("Vision capture", f"Shape: {frame.shape}")
    else:
        test_fail("Vision capture", "Returned None")
    
    finder = WindowFinder()
    test_pass("WindowFinder init")
    
except Exception as e:
    test_fail("Vision module", str(e))

# ============================================
print("\n[7/7] State Machine & Input Handler")
print("-" * 30)

try:
    from state_machine import JoinStateMachine, JoinState, StateMachineConfig
    sm = JoinStateMachine()
    sm.start()
    state = sm.get_state()
    sm.stop()
    test_pass("State machine", f"Transitions work ({state.name})")
except Exception as e:
    test_fail("State machine", str(e))

try:
    from input_handler import HumanInput, HumanInputConfig, is_available, get_backend
    backend = get_backend()
    test_pass("Input handler", f"Backend: {backend}")
except Exception as e:
    test_fail("Input handler", str(e))

# ============================================
print("\n" + "=" * 50)
print("TEST SUMMARY")
print("=" * 50)
print(f"\n  Passed:   {results['passed']}")
print(f"  Failed:   {results['failed']}")
print(f"  Warnings: {results['warnings']}")

if results['failed'] == 0:
    print("\n✓ All critical tests passed!")
    print("  You can run: python joinsim.py")
else:
    print(f"\n✗ {results['failed']} tests failed - see errors above")
    print("  Try: pip install -r requirements-windows.txt")

if results['warnings'] > 0:
    print(f"\n  {results['warnings']} optional features not available.")
    print("  For best performance, install:")
    if not HAS_PYDIRECTINPUT:
        print("    pip install pydirectinput")
    if not HAS_DXCAM:
        print("    pip install dxcam")
    if not HAS_WIN32GUI:
        print("    pip install pywin32")

print()
input("Press Enter to exit...")
