"""Quick test to verify all dependencies are installed correctly."""

print("Testing imports...")

try:
    import pyautogui
    print("✅ pyautogui OK")
except ImportError as e:
    print(f"❌ pyautogui FAILED: {e}")

try:
    import keyboard
    print("✅ keyboard OK")
except ImportError as e:
    print(f"❌ keyboard FAILED: {e}")

try:
    from pynput import mouse
    print("✅ pynput OK")
except ImportError as e:
    print(f"❌ pynput FAILED: {e}")

try:
    from PIL import Image
    print("✅ Pillow OK")
except ImportError as e:
    print(f"❌ Pillow FAILED: {e}")

try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.destroy()
    print("✅ tkinter OK")
except Exception as e:
    print(f"❌ tkinter FAILED: {e}")

print("\n✅ All tests passed!" if all([
    'pyautogui' in dir(),
    'keyboard' in dir(),
    'mouse' in dir(),
    'Image' in dir(),
]) else "\n⚠️ Some imports failed - run: pip install -r requirements.txt")

input("\nPress Enter to exit...")
