#!/usr/bin/env python3
"""
Comprehensive component test for Ark JoinSim.
Tests all modules without requiring the actual game.

Usage:
    python test_components.py
    python test_components.py --visual  # Test UI if available
"""

import sys
import os
import argparse
from pathlib import Path

# Test results tracking
results = {
    "passed": [],
    "failed": [],
    "skipped": []
}


def test_pass(name: str, msg: str = ""):
    """Record a passing test."""
    results["passed"].append(name)
    print(f"  [OK] {name}" + (f" - {msg}" if msg else ""))


def test_fail(name: str, msg: str = ""):
    """Record a failing test."""
    results["failed"].append(name)
    print(f"  [FAIL] {name}" + (f" - {msg}" if msg else ""))


def test_skip(name: str, msg: str = ""):
    """Record a skipped test."""
    results["skipped"].append(name)
    print(f"  [SKIP] {name}" + (f" - {msg}" if msg else ""))


def test_vision_module():
    """Test the vision module components."""
    print("\n=== Vision Module Tests ===")
    
    # Test imports
    try:
        from vision import ScreenCapture, TemplateDetector, WindowFinder
        test_pass("Import vision module")
    except ImportError as e:
        test_fail("Import vision module", str(e))
        return
    
    # Test ScreenCapture
    try:
        cap = ScreenCapture(use_dxcam=False)
        frame = cap.capture()
        if frame is not None and len(frame.shape) == 3:
            test_pass("Screen capture", f"Shape: {frame.shape}")
        else:
            test_fail("Screen capture", "Got None or invalid shape")
    except Exception as e:
        test_fail("Screen capture", str(e))
    
    # Test WindowFinder (will find None if game not running)
    try:
        finder = WindowFinder()
        window = finder.find_window()
        # Window not found is OK - game isn't running
        test_pass("Window finder", f"Found: {window is not None}")
    except Exception as e:
        test_fail("Window finder", str(e))
    
    # Test TemplateDetector initialization
    try:
        cap = ScreenCapture(use_dxcam=False)
        templates_dir = Path(__file__).parent / "templates"
        detector = TemplateDetector(cap, templates_dir)
        test_pass("Template detector init")
    except Exception as e:
        test_fail("Template detector init", str(e))


def test_input_handler():
    """Test the input handler module."""
    print("\n=== Input Handler Tests ===")
    
    try:
        from input_handler import HumanInput, HumanInputConfig, is_available
        test_pass("Import input_handler")
    except ImportError as e:
        test_fail("Import input_handler", str(e))
        return
    
    # Test availability check
    try:
        available = is_available()
        test_pass("Input availability check", f"Available: {available}")
    except Exception as e:
        test_fail("Input availability check", str(e))
    
    # Test config creation
    try:
        config = HumanInputConfig(
            position_jitter=5,
            click_duration_min=0.05,
            click_duration_max=0.15,
        )
        test_pass("HumanInputConfig creation")
    except Exception as e:
        test_fail("HumanInputConfig creation", str(e))
    
    # Test HumanInput initialization (don't actually move mouse)
    try:
        config = HumanInputConfig()
        handler = HumanInput(config)
        test_pass("HumanInput initialization")
    except Exception as e:
        test_fail("HumanInput initialization", str(e))


def test_state_machine():
    """Test the state machine module."""
    print("\n=== State Machine Tests ===")
    
    try:
        from state_machine import JoinStateMachine, JoinState, StateMachineConfig
        test_pass("Import state_machine")
    except ImportError as e:
        test_fail("Import state_machine", str(e))
        return
    
    # Test config creation
    try:
        config = StateMachineConfig(timeout_seconds=15.0)
        test_pass("StateMachineConfig creation")
    except Exception as e:
        test_fail("StateMachineConfig creation", str(e))
    
    # Test state machine creation
    try:
        config = StateMachineConfig()
        sm = JoinStateMachine(config)
        test_pass("JoinStateMachine creation")
    except Exception as e:
        test_fail("JoinStateMachine creation", str(e))
    
    # Test state transitions
    try:
        config = StateMachineConfig()
        sm = JoinStateMachine(config)
        
        # Check initial state (use get_state() method)
        current = sm.get_state()
        if current == JoinState.IDLE:
            test_pass("Initial state is IDLE")
        else:
            test_fail("Initial state", f"Expected IDLE, got {current}")
        
        # Start and check state change
        sm.start()
        current = sm.get_state()
        if current == JoinState.SEARCHING:
            test_pass("State transitions to SEARCHING on start")
        else:
            test_fail("Start transition", f"Expected SEARCHING, got {current}")
        
        # Stop
        sm.stop()
        current = sm.get_state()
        if current == JoinState.IDLE:
            test_pass("State returns to IDLE on stop")
        else:
            test_fail("Stop transition", f"Expected IDLE, got {current}")
            
    except Exception as e:
        test_fail("State transitions", str(e))


def test_notifications():
    """Test the notifications module."""
    print("\n=== Notifications Tests ===")
    
    try:
        from notifications import Notifier
        test_pass("Import notifications")
    except ImportError as e:
        test_fail("Import notifications", str(e))
        return
    
    # Test notifier creation
    try:
        notifier = Notifier()
        test_pass("Notifier creation")
    except Exception as e:
        test_fail("Notifier creation", str(e))
    
    # Test configuration
    try:
        notifier = Notifier()
        notifier.set_sound_enabled(False)
        notifier.set_discord_webhook(None)
        test_pass("Notifier configuration")
    except Exception as e:
        test_fail("Notifier configuration", str(e))


def test_setup_wizard():
    """Test the setup wizard module."""
    print("\n=== Setup Wizard Tests ===")
    
    # Check if tkinter is available first
    try:
        import tkinter
    except ImportError:
        test_skip("Import setup_wizard", "Tkinter not available (required for GUI)")
        # Still test templates directory
        templates_dir = Path(__file__).parent / "templates"
        try:
            templates_dir.mkdir(parents=True, exist_ok=True)
            test_pass("Templates directory", str(templates_dir))
        except Exception as e:
            test_fail("Templates directory", str(e))
        return
    
    try:
        from setup_wizard import SetupWizard, TEMPLATES_DIR
        test_pass("Import setup_wizard")
    except ImportError as e:
        test_fail("Import setup_wizard", str(e))
        return
    
    # Test TEMPLATES_DIR exists or can be created
    try:
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        test_pass("Templates directory", str(TEMPLATES_DIR))
    except Exception as e:
        test_fail("Templates directory", str(e))
    
    # Test setup completion check
    try:
        complete = SetupWizard.is_setup_complete()
        test_pass("Setup completion check", f"Complete: {complete}")
    except Exception as e:
        test_fail("Setup completion check", str(e))


def test_ui_available():
    """Test if the UI (customtkinter) is available."""
    print("\n=== UI Availability Tests ===")
    
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        test_pass("Tkinter available")
    except Exception as e:
        test_fail("Tkinter available", str(e))
        return False
    
    try:
        import customtkinter as ctk
        test_pass("CustomTkinter available")
        return True
    except Exception as e:
        test_fail("CustomTkinter available", str(e))
        return False


def test_visual_ui():
    """Test the actual UI visually (requires display)."""
    print("\n=== Visual UI Tests ===")
    
    try:
        import customtkinter as ctk
    except ImportError:
        test_skip("Visual UI", "CustomTkinter not available")
        return
    
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        root = ctk.CTk()
        root.title("JoinSim UI Test")
        root.geometry("480x300")
        
        # Create test layout matching main app
        main = ctk.CTkFrame(root, corner_radius=0)
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Title
        ctk.CTkLabel(
            main,
            text="Ark JoinSim v4 - UI Test",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=10)
        
        # Status
        status = ctk.CTkFrame(main, fg_color="gray20", corner_radius=10, height=60)
        status.pack(fill="x", pady=10)
        status.pack_propagate(False)
        ctk.CTkLabel(
            status,
            text="UI TEST MODE",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#22C55E",
        ).pack(expand=True)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15, padx=10)
        
        btn_inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_inner.pack(expand=True)
        
        def on_close():
            test_pass("Close button clicked")
            root.quit()
        
        ctk.CTkButton(
            btn_inner,
            text="START",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=150,
            height=45,
            command=lambda: test_pass("Start button clicked"),
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_inner,
            text="Settings",
            font=ctk.CTkFont(size=14),
            width=150,
            height=45,
            fg_color="gray30",
            hover_color="gray40",
            command=lambda: test_pass("Settings button clicked"),
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_inner,
            text="Close Test",
            font=ctk.CTkFont(size=14),
            width=150,
            height=45,
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=on_close,
        ).pack(side="left", padx=10)
        
        # Info
        ctk.CTkLabel(
            main,
            text="Click buttons to test, then click 'Close Test'",
            text_color="gray50",
        ).pack(pady=10)
        
        test_pass("UI window created")
        
        # Run for 10 seconds max or until closed
        root.after(10000, root.quit)
        root.mainloop()
        
        test_pass("UI closed successfully")
        
    except Exception as e:
        test_fail("Visual UI test", str(e))


def print_summary():
    """Print test summary."""
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    total = len(results["passed"]) + len(results["failed"]) + len(results["skipped"])
    
    print(f"\n  Passed:  {len(results['passed'])}")
    print(f"  Failed:  {len(results['failed'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Total:   {total}")
    
    if results["failed"]:
        print("\n  Failed tests:")
        for name in results["failed"]:
            print(f"    - {name}")
    
    print()
    
    return len(results["failed"]) == 0


def main():
    parser = argparse.ArgumentParser(description="Test Ark JoinSim components")
    parser.add_argument("--visual", action="store_true", help="Run visual UI tests")
    args = parser.parse_args()
    
    print("=" * 50)
    print("ARK JOINSIM COMPONENT TESTS")
    print("=" * 50)
    
    # Run non-visual tests
    test_vision_module()
    test_input_handler()
    test_state_machine()
    test_notifications()
    test_setup_wizard()
    
    # Check UI availability
    ui_available = test_ui_available()
    
    # Run visual tests if requested and available
    if args.visual:
        if ui_available:
            test_visual_ui()
        else:
            print("\n=== Visual UI Tests ===")
            test_skip("Visual UI", "Tkinter/CustomTkinter not available")
    
    # Print summary
    success = print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
