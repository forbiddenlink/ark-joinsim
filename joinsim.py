"""
Ark JoinSim — Auto-Joiner for Ark: Survival Ascended
Automatically clicks the Join button to get into full servers.

Usage:
    python joinsim.py

Hotkeys:
    F6 - Start/Stop auto-clicking
    F7 - Quit
"""

import json
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

try:
    import pyautogui
    import keyboard
except ImportError:
    print("Missing dependencies. Run: pip install pyautogui keyboard")
    exit(1)

# Disable PyAutoGUI fail-safe (move mouse to corner to stop)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

CONFIG_FILE = Path(__file__).parent / "joinsim_config.json"

DEFAULT_CONFIG = {
    "click_x": None,
    "click_y": None,
    "interval": 2.0,
    "jitter": 0.5,
    "resolution": None,
}


class JoinSim:
    def __init__(self):
        self.config = self.load_config()
        self.running = False
        self.click_thread = None
        self.setting_position = False
        
        # GUI
        self.root = tk.Tk()
        self.root.title("Ark JoinSim")
        self.root.geometry("400x350")
        self.root.resizable(False, False)
        
        # Try to set dark theme
        try:
            self.root.tk.call("source", "azure.tcl")
            self.root.tk.call("set_theme", "dark")
        except:
            pass
        
        self.setup_ui()
        self.setup_hotkeys()
        
        # Update resolution on start
        self.update_resolution()
    
    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    cfg = json.load(f)
                    return {**DEFAULT_CONFIG, **cfg}
            except:
                pass
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def update_resolution(self):
        width, height = pyautogui.size()
        self.config["resolution"] = f"{width}x{height}"
        self.res_label.config(text=f"Screen: {width}x{height}")
    
    def setup_ui(self):
        # Title
        title = ttk.Label(self.root, text="🦖 Ark JoinSim", font=("Helvetica", 18, "bold"))
        title.pack(pady=15)
        
        # Status
        self.status_var = tk.StringVar(value="⏸️ Stopped")
        status = ttk.Label(self.root, textvariable=self.status_var, font=("Helvetica", 14))
        status.pack(pady=5)
        
        # Resolution
        self.res_label = ttk.Label(self.root, text="Screen: detecting...", font=("Helvetica", 10))
        self.res_label.pack(pady=2)
        
        # Click position
        pos_frame = ttk.Frame(self.root)
        pos_frame.pack(pady=10)
        
        self.pos_label = ttk.Label(pos_frame, text=self.get_pos_text(), font=("Helvetica", 10))
        self.pos_label.pack(side=tk.LEFT, padx=5)
        
        set_pos_btn = ttk.Button(pos_frame, text="Set Position", command=self.start_set_position)
        set_pos_btn.pack(side=tk.LEFT, padx=5)
        
        # Interval
        interval_frame = ttk.Frame(self.root)
        interval_frame.pack(pady=10)
        
        ttk.Label(interval_frame, text="Interval (sec):").pack(side=tk.LEFT, padx=5)
        self.interval_var = tk.StringVar(value=str(self.config["interval"]))
        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=8)
        interval_entry.pack(side=tk.LEFT, padx=5)
        interval_entry.bind("<FocusOut>", self.update_interval)
        
        # Jitter
        jitter_frame = ttk.Frame(self.root)
        jitter_frame.pack(pady=5)
        
        ttk.Label(jitter_frame, text="Random jitter ±(sec):").pack(side=tk.LEFT, padx=5)
        self.jitter_var = tk.StringVar(value=str(self.config["jitter"]))
        jitter_entry = ttk.Entry(jitter_frame, textvariable=self.jitter_var, width=8)
        jitter_entry.pack(side=tk.LEFT, padx=5)
        jitter_entry.bind("<FocusOut>", self.update_jitter)
        
        # Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20)
        
        self.start_btn = ttk.Button(btn_frame, text="▶️ Start (F6)", command=self.toggle, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        quit_btn = ttk.Button(btn_frame, text="❌ Quit (F7)", command=self.quit, width=15)
        quit_btn.pack(side=tk.LEFT, padx=10)
        
        # Instructions
        instructions = ttk.Label(
            self.root,
            text="1. Click 'Set Position' then click Ark's Join button\n"
                 "2. Press Start or F6 to begin auto-clicking\n"
                 "3. F6 to pause, F7 to quit",
            font=("Helvetica", 9),
            justify=tk.CENTER
        )
        instructions.pack(pady=10)
    
    def get_pos_text(self):
        x, y = self.config.get("click_x"), self.config.get("click_y")
        if x is not None and y is not None:
            return f"Click at: ({x}, {y})"
        return "Click at: Not set"
    
    def setup_hotkeys(self):
        keyboard.add_hotkey("F6", self.toggle)
        keyboard.add_hotkey("F7", self.quit)
    
    def start_set_position(self):
        self.setting_position = True
        self.status_var.set("🎯 Click the Join button in Ark...")
        self.root.after(100, self.wait_for_click)
    
    def wait_for_click(self):
        if not self.setting_position:
            return
        
        import pynput.mouse as mouse
        
        def on_click(x, y, button, pressed):
            if pressed and self.setting_position:
                self.config["click_x"] = x
                self.config["click_y"] = y
                self.save_config()
                self.pos_label.config(text=self.get_pos_text())
                self.status_var.set("✅ Position set!")
                self.setting_position = False
                return False  # Stop listener
        
        listener = mouse.Listener(on_click=on_click)
        listener.start()
    
    def update_interval(self, event=None):
        try:
            val = float(self.interval_var.get())
            if val < 0.5:
                val = 0.5
            self.config["interval"] = val
            self.save_config()
        except ValueError:
            self.interval_var.set(str(self.config["interval"]))
    
    def update_jitter(self, event=None):
        try:
            val = float(self.jitter_var.get())
            if val < 0:
                val = 0
            self.config["jitter"] = val
            self.save_config()
        except ValueError:
            self.jitter_var.set(str(self.config["jitter"]))
    
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()
    
    def start(self):
        if self.config.get("click_x") is None:
            messagebox.showwarning("No Position", "Please set the click position first!")
            return
        
        self.running = True
        self.status_var.set("🟢 Running...")
        self.start_btn.config(text="⏸️ Pause (F6)")
        
        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.click_thread.start()
    
    def stop(self):
        self.running = False
        self.status_var.set("⏸️ Paused")
        self.start_btn.config(text="▶️ Start (F6)")
    
    def click_loop(self):
        while self.running:
            x = self.config["click_x"]
            y = self.config["click_y"]
            
            # Add jitter
            jitter = self.config.get("jitter", 0.5)
            x += random.randint(-3, 3)
            y += random.randint(-3, 3)
            
            # Click
            try:
                pyautogui.click(x, y)
            except Exception as e:
                print(f"Click error: {e}")
            
            # Wait with jitter
            interval = self.config["interval"]
            wait = interval + random.uniform(-jitter, jitter)
            wait = max(0.5, wait)
            time.sleep(wait)
    
    def quit(self):
        self.running = False
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        from pynput import mouse
    except ImportError:
        print("Missing pynput. Run: pip install pynput")
        exit(1)
    
    app = JoinSim()
    app.run()
