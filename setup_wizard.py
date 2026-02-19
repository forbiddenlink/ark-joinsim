"""
Template Capture Wizard for Ark JoinSim v4.

Guides users through capturing template images for vision-based automation.
Uses CustomTkinter for a modern dark UI.

Usage:
    python setup_wizard.py

    # Or from code:
    from setup_wizard import SetupWizard

    if not SetupWizard.is_setup_complete():
        wizard = SetupWizard()
        if wizard.run():
            print("Setup complete!")
        else:
            print("Setup cancelled")
"""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable

import numpy as np

try:
    import customtkinter as ctk
except ImportError:
    raise ImportError("CustomTkinter is required. Run: pip install customtkinter")

try:
    import keyboard
except ImportError:
    raise ImportError("keyboard is required. Run: pip install keyboard")

try:
    import pyautogui
except ImportError:
    raise ImportError("pyautogui is required. Run: pip install pyautogui")

try:
    import mss
except ImportError:
    raise ImportError("mss is required. Run: pip install mss")

try:
    from PIL import Image, ImageTk
except ImportError:
    raise ImportError("Pillow is required. Run: pip install pillow")


# Constants
TEMPLATES_DIR = Path(__file__).parent / "templates"
MANIFEST_FILE = TEMPLATES_DIR / "manifest.json"

# Capture region size (pixels around cursor)
DEFAULT_CAPTURE_WIDTH = 150
DEFAULT_CAPTURE_HEIGHT = 50

# Required templates for basic operation
REQUIRED_TEMPLATES = ["join_button", "server_full"]

# All capturable templates
TEMPLATE_CONFIGS = {
    "join_button": {
        "title": "Capture Join Button",
        "instructions": [
            "1. Open ARK and go to the server browser",
            "2. Find a server and hover over the JOIN button",
            "3. Press F8 to capture the button",
        ],
        "required": True,
        "capture_width": 150,
        "capture_height": 50,
    },
    "server_full": {
        "title": "Capture Server Full Popup",
        "instructions": [
            "1. Try to join a full server",
            "2. When the 'Server Full' popup appears,",
            "   hover over the message text",
            "3. Press F8 to capture",
        ],
        "required": True,
        "capture_width": 200,
        "capture_height": 60,
    },
    "server_list": {
        "title": "Capture Server List Area",
        "instructions": [
            "1. Open the server browser",
            "2. Hover over a distinctive part of the",
            "   server list (e.g., a column header)",
            "3. Press F8 to capture",
        ],
        "required": False,
        "capture_width": 200,
        "capture_height": 50,
    },
    "loading": {
        "title": "Capture Loading Screen (Optional)",
        "instructions": [
            "1. Join any server to trigger loading",
            "2. Hover over a distinctive loading element",
            "3. Press F8 to capture",
            "",
            "You can skip this step if not needed.",
        ],
        "required": False,
        "capture_width": 200,
        "capture_height": 60,
    },
}


class SetupWizard(ctk.CTk):
    """CustomTkinter wizard for capturing template images.

    Guides the user through capturing each required template image
    using F8 hotkey to capture the region around the mouse cursor.

    Attributes:
        completed: Whether setup was completed successfully.
        templates_captured: Dict of captured template names to file paths.
    """

    def __init__(self):
        """Initialize the Setup Wizard."""
        super().__init__()

        # Configure window
        self.title("Ark JoinSim - Setup Wizard")
        self.geometry("500x550")
        self.resizable(False, False)

        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State
        self.completed = False
        self.templates_captured: Dict[str, str] = {}
        self._current_step = 0
        self._steps = ["welcome"] + list(TEMPLATE_CONFIGS.keys()) + ["complete"]
        self._hotkey_registered = False
        self._waiting_for_capture = False
        self._captured_image: Optional[np.ndarray] = None
        self._preview_photo: Optional[ImageTk.PhotoImage] = None

        # Screen capture context
        self._mss_context: Optional[mss.mss] = None

        # Get screen resolution
        screen_width, screen_height = pyautogui.size()
        self._resolution = f"{screen_width}x{screen_height}"

        # Ensure templates directory exists
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        # Build UI
        self._build_ui()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self) -> None:
        """Build the wizard UI."""
        # Main container
        self._main_frame = ctk.CTkFrame(self, corner_radius=0)
        self._main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header with title and step indicator
        self._header_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._header_frame.pack(fill="x", pady=(0, 15))

        self._title_label = ctk.CTkLabel(
            self._header_frame,
            text="Setup Wizard",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self._title_label.pack(side="left")

        self._step_label = ctk.CTkLabel(
            self._header_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self._step_label.pack(side="right")

        # Separator
        self._separator = ctk.CTkFrame(self._main_frame, height=2, fg_color="gray30")
        self._separator.pack(fill="x", pady=(0, 15))

        # Content frame (will be rebuilt for each step)
        self._content_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._content_frame.pack(fill="both", expand=True)

        # Status label
        self._status_label = ctk.CTkLabel(
            self._main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self._status_label.pack(pady=(10, 0))

        # Button frame
        self._button_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._button_frame.pack(fill="x", pady=(15, 0))

        self._cancel_btn = ctk.CTkButton(
            self._button_frame,
            text="Cancel",
            width=100,
            fg_color="gray30",
            hover_color="gray40",
            command=self._on_cancel,
        )
        self._cancel_btn.pack(side="left")

        self._next_btn = ctk.CTkButton(
            self._button_frame,
            text="Next",
            width=100,
            command=self._on_next,
        )
        self._next_btn.pack(side="right")

        self._back_btn = ctk.CTkButton(
            self._button_frame,
            text="Back",
            width=100,
            fg_color="gray30",
            hover_color="gray40",
            command=self._on_back,
        )
        self._back_btn.pack(side="right", padx=(0, 10))

        self._skip_btn = ctk.CTkButton(
            self._button_frame,
            text="Skip",
            width=100,
            fg_color="gray30",
            hover_color="gray40",
            command=self._on_skip,
        )
        self._skip_btn.pack(side="right", padx=(0, 10))

        # Show first step
        self._show_step(0)

    def _clear_content(self) -> None:
        """Clear the content frame."""
        for widget in self._content_frame.winfo_children():
            widget.destroy()

    def _show_step(self, step_index: int) -> None:
        """Show a specific wizard step.

        Args:
            step_index: Index of the step to show.
        """
        self._current_step = step_index
        step_name = self._steps[step_index]

        # Update step indicator
        total_steps = len(self._steps)
        self._step_label.configure(text=f"Step {step_index + 1} of {total_steps}")

        # Clear content
        self._clear_content()

        # Reset capture state
        self._waiting_for_capture = False
        self._captured_image = None
        self._status_label.configure(text="")

        # Show appropriate content
        if step_name == "welcome":
            self._show_welcome()
        elif step_name == "complete":
            self._show_complete()
        else:
            self._show_capture_step(step_name)

        # Update button visibility
        self._update_buttons()

    def _show_welcome(self) -> None:
        """Show the welcome step."""
        self._title_label.configure(text="Welcome to Setup")

        # Welcome text
        welcome_text = ctk.CTkLabel(
            self._content_frame,
            text="This wizard will help you capture template\nimages for ARK JoinSim's vision system.",
            font=ctk.CTkFont(size=14),
            justify="center",
        )
        welcome_text.pack(pady=(20, 15))

        # What you'll need
        needs_label = ctk.CTkLabel(
            self._content_frame,
            text="What you'll need:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        needs_label.pack(fill="x", pady=(15, 5))

        needs_items = [
            "ARK: Survival Ascended running",
            "Access to the server browser",
            "A full server to capture the popup",
        ]

        for item in needs_items:
            item_label = ctk.CTkLabel(
                self._content_frame,
                text=f"  - {item}",
                font=ctk.CTkFont(size=12),
                anchor="w",
            )
            item_label.pack(fill="x")

        # How it works
        how_label = ctk.CTkLabel(
            self._content_frame,
            text="\nHow it works:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        how_label.pack(fill="x", pady=(15, 5))

        how_items = [
            "Position your mouse over the target element",
            "Press F8 to capture a region around your cursor",
            "The captured image will be saved as a template",
        ]

        for item in how_items:
            item_label = ctk.CTkLabel(
                self._content_frame,
                text=f"  - {item}",
                font=ctk.CTkFont(size=12),
                anchor="w",
            )
            item_label.pack(fill="x")

        # Resolution info
        res_label = ctk.CTkLabel(
            self._content_frame,
            text=f"\nDetected resolution: {self._resolution}",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        res_label.pack(pady=(20, 0))

    def _show_capture_step(self, template_name: str) -> None:
        """Show a template capture step.

        Args:
            template_name: Name of the template to capture.
        """
        config = TEMPLATE_CONFIGS[template_name]

        self._title_label.configure(text=config["title"])

        # Instructions
        for instruction in config["instructions"]:
            if instruction:
                inst_label = ctk.CTkLabel(
                    self._content_frame,
                    text=instruction,
                    font=ctk.CTkFont(size=13),
                    anchor="w",
                )
                inst_label.pack(fill="x", pady=2)
            else:
                # Empty line
                spacer = ctk.CTkLabel(self._content_frame, text="")
                spacer.pack()

        # Preview frame
        self._preview_frame = ctk.CTkFrame(
            self._content_frame,
            width=250,
            height=100,
            fg_color="gray20",
            corner_radius=8,
        )
        self._preview_frame.pack(pady=20)
        self._preview_frame.pack_propagate(False)

        # Preview label (image or placeholder)
        self._preview_label = ctk.CTkLabel(
            self._preview_frame,
            text="Press F8 to capture",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self._preview_label.pack(expand=True)

        # Check if already captured
        if template_name in self.templates_captured:
            self._load_existing_preview(template_name)

        # Register F8 hotkey
        self._register_hotkey(template_name, config)

        # Update status
        self._status_label.configure(text="Waiting for F8...")
        self._waiting_for_capture = True

    def _show_complete(self) -> None:
        """Show the completion step."""
        self._title_label.configure(text="Setup Complete!")

        # Unregister hotkey
        self._unregister_hotkey()

        # Success message
        success_label = ctk.CTkLabel(
            self._content_frame,
            text="All templates have been captured successfully!",
            font=ctk.CTkFont(size=14),
        )
        success_label.pack(pady=(30, 20))

        # Summary
        summary_label = ctk.CTkLabel(
            self._content_frame,
            text="Captured templates:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        summary_label.pack(fill="x", pady=(10, 5))

        for name, path in self.templates_captured.items():
            item_label = ctk.CTkLabel(
                self._content_frame,
                text=f"  - {name}: {Path(path).name}",
                font=ctk.CTkFont(size=12),
                anchor="w",
                text_color="green",
            )
            item_label.pack(fill="x")

        # Skipped templates
        skipped = [
            name
            for name in TEMPLATE_CONFIGS.keys()
            if name not in self.templates_captured
        ]
        if skipped:
            skipped_label = ctk.CTkLabel(
                self._content_frame,
                text="\nSkipped (optional):",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            )
            skipped_label.pack(fill="x", pady=(10, 5))

            for name in skipped:
                item_label = ctk.CTkLabel(
                    self._content_frame,
                    text=f"  - {name}",
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    text_color="gray",
                )
                item_label.pack(fill="x")

        # Info
        info_label = ctk.CTkLabel(
            self._content_frame,
            text="\nTemplates saved to: templates/",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        info_label.pack(pady=(20, 0))

        self._status_label.configure(text="Click Finish to close the wizard.")

    def _update_buttons(self) -> None:
        """Update button visibility based on current step."""
        step_name = self._steps[self._current_step]

        # Back button
        if self._current_step == 0:
            self._back_btn.pack_forget()
        else:
            self._back_btn.pack(side="right", padx=(0, 10))

        # Skip button (only for optional templates)
        if step_name in TEMPLATE_CONFIGS:
            config = TEMPLATE_CONFIGS[step_name]
            if not config["required"]:
                self._skip_btn.pack(side="right", padx=(0, 10))
            else:
                self._skip_btn.pack_forget()
        else:
            self._skip_btn.pack_forget()

        # Next button text
        if step_name == "welcome":
            self._next_btn.configure(text="Start")
        elif step_name == "complete":
            self._next_btn.configure(text="Finish")
        else:
            self._next_btn.configure(text="Next")

        # Next button state (disabled if required template not captured)
        if step_name in TEMPLATE_CONFIGS:
            config = TEMPLATE_CONFIGS[step_name]
            if config["required"] and step_name not in self.templates_captured:
                self._next_btn.configure(state="disabled")
            else:
                self._next_btn.configure(state="normal")
        else:
            self._next_btn.configure(state="normal")

    def _register_hotkey(self, template_name: str, config: Dict[str, Any]) -> None:
        """Register the F8 hotkey for capture.

        Args:
            template_name: Name of the template to capture.
            config: Template configuration.
        """
        self._unregister_hotkey()

        def on_f8():
            if self._waiting_for_capture:
                self._capture_template(
                    template_name,
                    config["capture_width"],
                    config["capture_height"],
                )

        keyboard.add_hotkey("F8", on_f8)
        self._hotkey_registered = True

    def _unregister_hotkey(self) -> None:
        """Unregister the F8 hotkey."""
        if self._hotkey_registered:
            try:
                keyboard.remove_hotkey("F8")
            except (KeyError, ValueError):
                pass
            self._hotkey_registered = False

    def _capture_template(
        self, template_name: str, width: int, height: int
    ) -> None:
        """Capture a template image around the cursor.

        Args:
            template_name: Name for the template.
            width: Width of capture region.
            height: Height of capture region.
        """
        # Get mouse position
        mouse_x, mouse_y = pyautogui.position()

        # Calculate capture region (centered on cursor)
        left = max(0, mouse_x - width // 2)
        top = max(0, mouse_y - height // 2)
        right = left + width
        bottom = top + height

        # Capture screen region
        try:
            if self._mss_context is None:
                self._mss_context = mss.mss()

            monitor = {
                "left": left,
                "top": top,
                "width": width,
                "height": height,
            }

            screenshot = self._mss_context.grab(monitor)

            # Convert to numpy array (BGRA)
            img_array = np.array(screenshot)

            # Save the image
            filename = f"{template_name}_{self._resolution}.png"
            filepath = TEMPLATES_DIR / filename

            # Use PIL to save (convert BGRA to RGB)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.save(str(filepath))

            # Store captured info
            self.templates_captured[template_name] = str(filepath)
            self._captured_image = img_array

            # Update manifest
            self._save_manifest()

            # Update UI (schedule on main thread)
            self.after(0, lambda: self._on_capture_success(template_name, img))

        except Exception as e:
            self.after(0, lambda: self._on_capture_error(str(e)))

    def _on_capture_success(self, template_name: str, img: Image.Image) -> None:
        """Handle successful capture.

        Args:
            template_name: Name of the captured template.
            img: Captured PIL Image.
        """
        self._waiting_for_capture = False
        self._status_label.configure(text=f"Captured {template_name}!", text_color="green")

        # Show preview
        self._show_preview(img)

        # Update buttons
        self._update_buttons()

    def _on_capture_error(self, error: str) -> None:
        """Handle capture error.

        Args:
            error: Error message.
        """
        self._status_label.configure(text=f"Error: {error}", text_color="red")

    def _show_preview(self, img: Image.Image) -> None:
        """Show a preview of the captured image.

        Args:
            img: PIL Image to preview.
        """
        # Resize if needed to fit preview frame
        max_width = 230
        max_height = 80

        # Calculate scale
        scale = min(max_width / img.width, max_height / img.height, 1.0)
        new_size = (int(img.width * scale), int(img.height * scale))

        if scale < 1.0:
            img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            img_resized = img

        # Convert to PhotoImage
        self._preview_photo = ImageTk.PhotoImage(img_resized)

        # Update preview label
        self._preview_label.configure(image=self._preview_photo, text="")

    def _load_existing_preview(self, template_name: str) -> None:
        """Load and show preview of an existing captured template.

        Args:
            template_name: Name of the template.
        """
        if template_name not in self.templates_captured:
            return

        filepath = Path(self.templates_captured[template_name])
        if filepath.exists():
            try:
                img = Image.open(filepath)
                self._show_preview(img)
                self._status_label.configure(
                    text="Already captured. Press F8 to recapture.",
                    text_color="gray",
                )
            except Exception:
                pass

    def _save_manifest(self) -> None:
        """Save the manifest.json file."""
        manifest = {
            "resolution": self._resolution,
            "templates": {},
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

        for name, path in self.templates_captured.items():
            manifest["templates"][name] = Path(path).name

        with open(MANIFEST_FILE, "w") as f:
            json.dump(manifest, f, indent=4)

    def _on_next(self) -> None:
        """Handle Next button click."""
        step_name = self._steps[self._current_step]

        if step_name == "complete":
            # Finish wizard
            self.completed = True
            self._cleanup_and_close()
        elif self._current_step < len(self._steps) - 1:
            self._show_step(self._current_step + 1)

    def _on_back(self) -> None:
        """Handle Back button click."""
        if self._current_step > 0:
            self._show_step(self._current_step - 1)

    def _on_skip(self) -> None:
        """Handle Skip button click."""
        if self._current_step < len(self._steps) - 1:
            self._show_step(self._current_step + 1)

    def _on_cancel(self) -> None:
        """Handle Cancel button or window close."""
        self.completed = False
        self._cleanup_and_close()

    def _cleanup_and_close(self) -> None:
        """Clean up resources and close the wizard."""
        self._unregister_hotkey()

        if self._mss_context:
            try:
                self._mss_context.close()
            except Exception:
                pass
            self._mss_context = None

        self.destroy()

    def run(self) -> bool:
        """Run the wizard and block until complete.

        Returns:
            True if setup completed successfully, False if cancelled.
        """
        self.mainloop()
        return self.completed

    @staticmethod
    def is_setup_complete() -> bool:
        """Check if all required templates exist.

        Returns:
            True if setup is complete and all required templates exist.
        """
        if not MANIFEST_FILE.exists():
            return False

        try:
            with open(MANIFEST_FILE) as f:
                manifest = json.load(f)

            templates = manifest.get("templates", {})

            # Check all required templates exist
            for template_name in REQUIRED_TEMPLATES:
                if template_name not in templates:
                    return False

                # Verify file exists
                filename = templates[template_name]
                filepath = TEMPLATES_DIR / filename
                if not filepath.exists():
                    return False

            return True

        except (json.JSONDecodeError, KeyError, IOError):
            return False

    @staticmethod
    def get_template_path(template_name: str) -> Optional[Path]:
        """Get the path to a captured template.

        Args:
            template_name: Name of the template.

        Returns:
            Path to the template file, or None if not found.
        """
        if not MANIFEST_FILE.exists():
            return None

        try:
            with open(MANIFEST_FILE) as f:
                manifest = json.load(f)

            templates = manifest.get("templates", {})
            if template_name in templates:
                filepath = TEMPLATES_DIR / templates[template_name]
                if filepath.exists():
                    return filepath

        except (json.JSONDecodeError, KeyError, IOError):
            pass

        return None

    @staticmethod
    def get_resolution() -> Optional[str]:
        """Get the resolution that templates were captured at.

        Returns:
            Resolution string (e.g., "1920x1080") or None.
        """
        if not MANIFEST_FILE.exists():
            return None

        try:
            with open(MANIFEST_FILE) as f:
                manifest = json.load(f)

            return manifest.get("resolution")

        except (json.JSONDecodeError, KeyError, IOError):
            return None


def run_wizard() -> bool:
    """Run the setup wizard.

    Returns:
        True if setup completed successfully.
    """
    wizard = SetupWizard()
    return wizard.run()


if __name__ == "__main__":
    print("ARK JoinSim Setup Wizard")
    print("-" * 40)

    if SetupWizard.is_setup_complete():
        print("Setup is already complete!")
        print(f"Resolution: {SetupWizard.get_resolution()}")
        print("\nCaptured templates:")
        for template in REQUIRED_TEMPLATES:
            path = SetupWizard.get_template_path(template)
            if path:
                print(f"  - {template}: {path.name}")

        # Ask if they want to recapture
        response = input("\nRun wizard again to recapture? (y/n): ")
        if response.lower() != "y":
            exit(0)

    success = run_wizard()

    if success:
        print("\nSetup completed successfully!")
        print(f"Templates saved to: {TEMPLATES_DIR}")
    else:
        print("\nSetup was cancelled.")
