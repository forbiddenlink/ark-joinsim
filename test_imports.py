"""Quick test to verify all dependencies are installed correctly."""

print("Testing imports...")
print()

results = []

try:
    import pyautogui
    print("  pyautogui OK")
    results.append(True)
except ImportError as e:
    print(f"  pyautogui FAILED: {e}")
    results.append(False)

try:
    import keyboard
    print("  keyboard OK")
    results.append(True)
except ImportError as e:
    print(f"  keyboard FAILED: {e}")
    results.append(False)

try:
    from pynput import mouse
    print("  pynput OK")
    results.append(True)
except ImportError as e:
    print(f"  pynput FAILED: {e}")
    results.append(False)

try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.destroy()
    print("  tkinter OK")
    results.append(True)
except Exception as e:
    print(f"  tkinter FAILED: {e}")
    results.append(False)

print()
if all(results):
    print("All tests passed!")
else:
    print("Some imports failed - run: pip install -r requirements.txt")

input("\nPress Enter to exit...")
