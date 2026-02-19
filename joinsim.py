"""
Ark JoinSim v4 - Auto-Joiner for ARK: Survival Ascended
Modern CustomTkinter UI with vision-based automation.

Automatically detects the Join button and clicks it to get into full servers.
Uses template matching to detect server full popups and loading screens.

Usage:
    python joinsim.py

Hotkeys:
    F6 - Start/Stop auto-join
    F7 - Quit
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

try:
    import customtkinter as ctk
except ImportError:
    raise ImportError("CustomTkinter is required. Run: pip install customtkinter")

try:
    import keyboard
except ImportError:
    raise ImportError("keyboard is required. Run: pip install keyboard")

# Local modules
from vision import ScreenCapture, TemplateDetector, WindowFinder
from input_handler import HumanInput, HumanInputConfig, is_available as input_available
from state_machine import JoinStateMachine, JoinState, StateMachineConfig
from notifications import Notifier
from setup_wizard import SetupWizard, TEMPLATES_DIR

# Constants
CONFIG_FILE = Path(__file__).parent / "joinsim_config.json"

DEFAULT_CONFIG = {
    "timeout_seconds": 15.0,
    "sound_enabled": True,
    "discord_webhook_url": "",
    "position_jitter": 5,
    "click_duration_min": 0.05,
    "click_duration_max": 0.15,
    "detection_threshold": 0.8,
    "detection_interval_ms": 500,
}

# Status colors
STATUS_COLORS = {
    "idle": "#6B7280",       # Gray
    "searching": "#3B82F6",  # Blue
    "clicking": "#22C55E",   # Green
    "waiting": "#EAB308",    # Yellow
    "success": "#10B981",    # Bright green
    "error": "#EF4444",      # Red
    "retry": "#F59E0B",      # Orange
}


class ActivityLog:
    """Thread-safe scrollable activity log."""

    def __init__(self, parent: ctk.CTkFrame, max_lines: int = 100):
        """Initialize the activity log.

        Args:
            parent: Parent frame.
            max_lines: Maximum lines to keep.
        """
        self.max_lines = max_lines
        self._lines: list[str] = []

        # Create scrollable text box
        self._textbox = ctk.CTkTextbox(
            parent,
            height=120,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="gray15",
            text_color="gray70",
            state="disabled",
        )
        self._textbox.pack(fill="x", expand=True, padx=10, pady=(0, 10))

    def log(self, message: str) -> None:
        """Add a message to the log.

        Args:
            message: Message to add.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"{timestamp}  {message}"

        self._lines.append(line)

        # Trim if needed
        if len(self._lines) > self.max_lines:
            self._lines = self._lines[-self.max_lines:]

        # Update text (must be done on main thread)
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.insert("end", "\n".join(self._lines))
        self._textbox.see("end")
        self._textbox.configure(state="disabled")


class DetectionStatusPanel(ctk.CTkFrame):
    """Panel showing detection status for each element."""

    def __init__(self, parent: ctk.CTkFrame):
        """Initialize the detection status panel."""
        super().__init__(parent, fg_color="transparent")

        # Detection items
        self._items: Dict[str, ctk.CTkLabel] = {}

        items = [
            ("window", "ARK Window"),
            ("join_button", "Join Button"),
            ("server_full", "Server Full"),
            ("loading", "Loading"),
        ]

        for key, label in items:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=2)

            name_label = ctk.CTkLabel(
                row,
                text=f"{label}:",
                font=ctk.CTkFont(size=12),
                width=120,
                anchor="w",
            )
            name_label.pack(side="left")

            status_label = ctk.CTkLabel(
                row,
                text="Not detected",
                font=ctk.CTkFont(size=12),
                text_color="gray50",
            )
            status_label.pack(side="left")

            self._items[key] = status_label

    def update_status(
        self,
        key: str,
        detected: bool,
        extra: str = ""
    ) -> None:
        """Update a detection status.

        Args:
            key: Status key.
            detected: Whether detected.
            extra: Extra info (e.g., coordinates).
        """
        if key not in self._items:
            return

        label = self._items[key]
        if detected:
            text = "Found" if not extra else extra
            label.configure(text=text, text_color="#22C55E")
        else:
            label.configure(text="Not visible", text_color="gray50")


class SessionStatsPanel(ctk.CTkFrame):
    """Panel showing session statistics."""

    def __init__(self, parent: ctk.CTkFrame):
        """Initialize the session stats panel."""
        super().__init__(parent, fg_color="transparent")

        self._stats: Dict[str, ctk.CTkLabel] = {}

        stats = [
            ("retry_count", "Retry Count"),
            ("time_elapsed", "Time Elapsed"),
            ("clicks", "Clicks"),
        ]

        for key, label in stats:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=2)

            name_label = ctk.CTkLabel(
                row,
                text=f"{label}:",
                font=ctk.CTkFont(size=12),
                width=120,
                anchor="w",
            )
            name_label.pack(side="left")

            value_label = ctk.CTkLabel(
                row,
                text="0",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            value_label.pack(side="left")

            self._stats[key] = value_label

    def update_stat(self, key: str, value: str) -> None:
        """Update a statistic value.

        Args:
            key: Stat key.
            value: New value.
        """
        if key in self._stats:
            self._stats[key].configure(text=value)


class SettingsPopup(ctk.CTkToplevel):
    """Settings popup window."""

    def __init__(self, parent, config: dict, on_save: callable):
        """Initialize settings popup.

        Args:
            parent: Parent window.
            config: Current configuration.
            on_save: Callback when settings are saved.
        """
        super().__init__(parent)

        self.title("Settings")
        self.geometry("400x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._config = config.copy()
        self._on_save = on_save

        self._build_ui()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self) -> None:
        """Build the settings UI."""
        # Main frame
        main = ctk.CTkFrame(self, corner_radius=0)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = ctk.CTkLabel(
            main,
            text="Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(0, 15))

        # Timeout
        timeout_frame = ctk.CTkFrame(main, fg_color="transparent")
        timeout_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            timeout_frame,
            text="Timeout (seconds):",
            width=150,
            anchor="w",
        ).pack(side="left")

        self._timeout_var = ctk.StringVar(value=str(self._config.get("timeout_seconds", 15.0)))
        ctk.CTkEntry(
            timeout_frame,
            textvariable=self._timeout_var,
            width=80,
        ).pack(side="left")

        # Sound toggle
        sound_frame = ctk.CTkFrame(main, fg_color="transparent")
        sound_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            sound_frame,
            text="Sound Notifications:",
            width=150,
            anchor="w",
        ).pack(side="left")

        self._sound_var = ctk.BooleanVar(value=self._config.get("sound_enabled", True))
        ctk.CTkSwitch(
            sound_frame,
            text="",
            variable=self._sound_var,
        ).pack(side="left")

        # Detection threshold
        threshold_frame = ctk.CTkFrame(main, fg_color="transparent")
        threshold_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            threshold_frame,
            text="Detection Threshold:",
            width=150,
            anchor="w",
        ).pack(side="left")

        self._threshold_var = ctk.StringVar(value=str(self._config.get("detection_threshold", 0.8)))
        ctk.CTkEntry(
            threshold_frame,
            textvariable=self._threshold_var,
            width=80,
        ).pack(side="left")

        # Discord webhook
        webhook_frame = ctk.CTkFrame(main, fg_color="transparent")
        webhook_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            webhook_frame,
            text="Discord Webhook URL:",
            anchor="w",
        ).pack(fill="x")

        self._webhook_var = ctk.StringVar(value=self._config.get("discord_webhook_url", ""))
        ctk.CTkEntry(
            webhook_frame,
            textvariable=self._webhook_var,
            placeholder_text="https://discord.com/api/webhooks/...",
        ).pack(fill="x", pady=(5, 0))

        # Recapture templates button
        ctk.CTkButton(
            main,
            text="Recapture Templates",
            fg_color="gray30",
            hover_color="gray40",
            command=self._on_recapture,
        ).pack(pady=(20, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=80,
            fg_color="gray30",
            hover_color="gray40",
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Save",
            width=80,
            command=self._on_save_click,
        ).pack(side="right")

    def _on_save_click(self) -> None:
        """Handle save button click."""
        try:
            self._config["timeout_seconds"] = float(self._timeout_var.get())
            self._config["sound_enabled"] = self._sound_var.get()
            self._config["detection_threshold"] = float(self._threshold_var.get())
            self._config["discord_webhook_url"] = self._webhook_var.get().strip()

            self._on_save(self._config)
            self.destroy()
        except ValueError:
            pass  # Invalid input, ignore

    def _on_recapture(self) -> None:
        """Handle recapture templates button."""
        self.destroy()
        wizard = SetupWizard()
        wizard.mainloop()


class JoinSimApp(ctk.CTk):
    """Main JoinSim application with CustomTkinter UI."""

    def __init__(self):
        """Initialize the JoinSim application."""
        super().__init__()

        # Configure window
        self.title("Ark JoinSim v4")
        self.geometry("450x650")
        self.resizable(False, False)

        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Load config
        self._config = self._load_config()

        # Initialize components
        self._notifier = Notifier()
        self._notifier.set_sound_enabled(self._config.get("sound_enabled", True))
        self._notifier.set_discord_webhook(self._config.get("discord_webhook_url") or None)

        # Vision components (initialized lazily)
        self._window_finder: Optional[WindowFinder] = None
        self._screen_capture: Optional[ScreenCapture] = None
        self._template_detector: Optional[TemplateDetector] = None

        # Input handler
        self._input_handler: Optional[HumanInput] = None

        # State machine
        self._state_machine: Optional[JoinStateMachine] = None

        # Threading
        self._running = False
        self._detection_thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None

        # Build UI
        self._build_ui()

        # Setup hotkeys
        self._setup_hotkeys()

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_quit)

        # Check for templates
        self.after(100, self._check_templates)

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
            except (json.JSONDecodeError, IOError):
                pass
        return DEFAULT_CONFIG.copy()

    def _save_config(self) -> None:
        """Save configuration to file."""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=2)

    def _build_ui(self) -> None:
        """Build the main UI."""
        # Main container
        self._main_frame = ctk.CTkFrame(self, corner_radius=0)
        self._main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Header
        header = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            header,
            text="Ark JoinSim v4",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(side="left")

        # Status indicator (large, centered)
        status_frame = ctk.CTkFrame(
            self._main_frame,
            fg_color="gray20",
            corner_radius=10,
            height=80,
        )
        status_frame.pack(fill="x", pady=10)
        status_frame.pack_propagate(False)

        self._status_indicator = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(size=16),
            text_color=STATUS_COLORS["idle"],
        )
        self._status_indicator.pack(expand=True)

        self._status_text = ctk.CTkLabel(
            status_frame,
            text="STOPPED",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=STATUS_COLORS["idle"],
        )
        self._status_text.pack(expand=True)

        # Detection Status section
        det_section = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        det_section.pack(fill="x", pady=(10, 5))

        ctk.CTkLabel(
            det_section,
            text="Detection Status",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        self._detection_panel = DetectionStatusPanel(det_section)
        self._detection_panel.pack(fill="x", pady=(5, 0), padx=10)

        # Session Stats section
        stats_section = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        stats_section.pack(fill="x", pady=(10, 5))

        ctk.CTkLabel(
            stats_section,
            text="Session Stats",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        self._stats_panel = SessionStatsPanel(stats_section)
        self._stats_panel.pack(fill="x", pady=(5, 0), padx=10)

        # Buttons
        btn_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)

        self._start_btn = ctk.CTkButton(
            btn_frame,
            text="START",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=140,
            height=45,
            command=self._toggle,
        )
        self._start_btn.pack(side="left", padx=(30, 10))

        self._settings_btn = ctk.CTkButton(
            btn_frame,
            text="Settings",
            font=ctk.CTkFont(size=14),
            width=140,
            height=45,
            fg_color="gray30",
            hover_color="gray40",
            command=self._open_settings,
        )
        self._settings_btn.pack(side="right", padx=(10, 30))

        # Activity Log section
        log_section = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        log_section.pack(fill="both", expand=True, pady=(10, 0))

        ctk.CTkLabel(
            log_section,
            text="Activity Log",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        self._activity_log = ActivityLog(log_section)

        # Hotkey hint
        hint = ctk.CTkLabel(
            self._main_frame,
            text="F6: Start/Stop  |  F7: Quit",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        hint.pack(pady=(5, 0))

    def _setup_hotkeys(self) -> None:
        """Setup global hotkeys."""
        keyboard.add_hotkey("F6", self._toggle)
        keyboard.add_hotkey("F7", self._on_quit)

    def _check_templates(self) -> None:
        """Check if templates exist, launch wizard if not."""
        if not SetupWizard.is_setup_complete():
            self._log("Templates not found. Launching setup wizard...")
            self.withdraw()  # Hide main window

            wizard = SetupWizard()
            success = wizard.run()

            self.deiconify()  # Show main window again

            if success:
                self._log("Setup complete! Templates captured.")
            else:
                self._log("Setup cancelled. Some features may not work.")
        else:
            self._log("Templates loaded successfully.")
            res = SetupWizard.get_resolution()
            if res:
                self._log(f"Template resolution: {res}")

    def _initialize_components(self) -> bool:
        """Initialize vision and input components.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Window finder
            if self._window_finder is None:
                self._window_finder = WindowFinder()

            # Screen capture
            if self._screen_capture is None:
                self._screen_capture = ScreenCapture(use_dxcam=True)

            # Template detector
            if self._template_detector is None:
                self._template_detector = TemplateDetector(
                    self._screen_capture,
                    TEMPLATES_DIR,
                )

            # Input handler
            if self._input_handler is None:
                if not input_available():
                    self._log("ERROR: No input backend available!")
                    return False

                config = HumanInputConfig(
                    position_jitter=self._config.get("position_jitter", 5),
                    click_duration_min=self._config.get("click_duration_min", 0.05),
                    click_duration_max=self._config.get("click_duration_max", 0.15),
                )
                self._input_handler = HumanInput(config)

            # State machine
            if self._state_machine is None:
                sm_config = StateMachineConfig(
                    timeout_seconds=self._config.get("timeout_seconds", 15.0),
                )
                self._state_machine = JoinStateMachine(sm_config)
                self._state_machine.on_state_change(self._on_state_change)

            return True

        except Exception as e:
            self._log(f"ERROR initializing: {e}")
            return False

    def _toggle(self) -> None:
        """Toggle start/stop."""
        if self._running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        """Start the auto-join process."""
        if self._running:
            return

        # Check templates
        if not SetupWizard.is_setup_complete():
            self._log("ERROR: Templates not captured. Run setup first.")
            return

        # Initialize components
        if not self._initialize_components():
            return

        self._running = True
        self._start_time = time.time()

        # Update UI
        self._start_btn.configure(text="STOP")
        self._update_status("searching", "SEARCHING")

        # Start state machine
        if self._state_machine:
            self._state_machine.start()

        # Notify
        self._notifier.notify("start", "Auto-join started")
        self._log("Auto-join started")

        # Start detection thread
        self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._detection_thread.start()

    def _stop(self, reason: str = "User stopped") -> None:
        """Stop the auto-join process.

        Args:
            reason: Reason for stopping.
        """
        if not self._running:
            return

        self._running = False

        # Stop state machine
        if self._state_machine:
            self._state_machine.stop()

        # Update UI
        self._start_btn.configure(text="START")
        self._update_status("idle", "STOPPED")

        # Notify
        self._notifier.notify("stop", f"Auto-join stopped: {reason}")
        self._log(f"Stopped: {reason}")

    def _detection_loop(self) -> None:
        """Main detection loop running in background thread."""
        interval = self._config.get("detection_interval_ms", 500) / 1000.0
        threshold = self._config.get("detection_threshold", 0.8)

        while self._running:
            try:
                # Get window region
                region = None
                window_found = False

                if self._window_finder:
                    region = self._window_finder.get_window_region()
                    window_found = region is not None

                # Prepare detections dict
                detections: Dict[str, Any] = {
                    "window_found": window_found,
                    "join_button": None,
                    "server_full": False,
                    "server_list": False,
                    "loading": False,
                    "spawn_screen": False,
                }

                if window_found and self._template_detector:
                    # Find join button
                    join_pos = self._template_detector.find_template(
                        "join_button",
                        threshold=threshold,
                        region=region,
                    )
                    detections["join_button"] = join_pos

                    # Check server full
                    detections["server_full"] = self._template_detector.can_see(
                        "server_full",
                        threshold=threshold,
                        region=region,
                    )

                    # Check loading (if template exists)
                    if SetupWizard.get_template_path("loading"):
                        detections["loading"] = self._template_detector.can_see(
                            "loading",
                            threshold=threshold,
                            region=region,
                        )

                    # Check server list (if template exists)
                    if SetupWizard.get_template_path("server_list"):
                        detections["server_list"] = self._template_detector.can_see(
                            "server_list",
                            threshold=threshold,
                            region=region,
                        )

                # Update UI detection panel
                self._update_detection_ui(detections, region)

                # Update state machine
                if self._state_machine:
                    action = self._state_machine.update(detections)

                    # Handle actions
                    if action == "click":
                        click_pos = self._state_machine.get_pending_click()
                        if click_pos and self._input_handler:
                            self._log(f"Clicking at ({click_pos[0]}, {click_pos[1]})")
                            self._input_handler.click(click_pos[0], click_pos[1])

                    elif action == "dismiss_popup":
                        # Press ESC to dismiss popup
                        if self._input_handler:
                            self._log("Dismissing popup (ESC)")
                            self._input_handler.press_key("escape")

                    # Update stats
                    info = self._state_machine.get_state_info()
                    self._update_stats_ui(info)

                    # Check for success
                    if self._state_machine.get_state() == JoinState.SUCCESS:
                        self.after(0, lambda: self._on_success())

            except Exception as e:
                self._log(f"Detection error: {e}")

            time.sleep(interval)

    def _update_detection_ui(self, detections: Dict[str, Any], region: Optional[Tuple[int, int, int, int]]) -> None:
        """Update detection panel in UI.

        Args:
            detections: Detection results.
            region: Window region.
        """
        def update():
            if region:
                width = region[2] - region[0]
                height = region[3] - region[1]
                self._detection_panel.update_status("window", True, f"Found ({width}x{height})")
            else:
                self._detection_panel.update_status("window", False)

            join_pos = detections.get("join_button")
            if join_pos:
                self._detection_panel.update_status("join_button", True, f"Located ({join_pos[0]}, {join_pos[1]})")
            else:
                self._detection_panel.update_status("join_button", False)

            self._detection_panel.update_status("server_full", detections.get("server_full", False))
            self._detection_panel.update_status("loading", detections.get("loading", False))

        self.after(0, update)

    def _update_stats_ui(self, info) -> None:
        """Update stats panel in UI.

        Args:
            info: StateInfo from state machine.
        """
        def update():
            self._stats_panel.update_stat("retry_count", str(info.retry_count))
            self._stats_panel.update_stat("clicks", str(info.total_clicks))

            # Calculate elapsed time
            if self._start_time:
                elapsed = time.time() - self._start_time
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                self._stats_panel.update_stat("time_elapsed", f"{minutes}:{seconds:02d}")

        self.after(0, update)

    def _on_state_change(self, old_state: JoinState, new_state: JoinState) -> None:
        """Handle state machine state changes.

        Args:
            old_state: Previous state.
            new_state: New state.
        """
        # Map states to UI status
        status_map = {
            JoinState.IDLE: ("idle", "STOPPED"),
            JoinState.SEARCHING: ("searching", "SEARCHING"),
            JoinState.CLICKING: ("clicking", "CLICKING"),
            JoinState.WAITING: ("waiting", "WAITING"),
            JoinState.SUCCESS: ("success", "SUCCESS!"),
            JoinState.FAILED_FULL: ("error", "SERVER FULL"),
            JoinState.FAILED_TIMEOUT: ("error", "TIMEOUT"),
            JoinState.RETRY: ("retry", "RETRYING"),
        }

        color_key, text = status_map.get(new_state, ("idle", "UNKNOWN"))

        self.after(0, lambda: self._update_status(color_key, text))
        self._log(f"State: {old_state.name} -> {new_state.name}")

        # Notify on specific states
        if new_state == JoinState.FAILED_FULL:
            self._notifier.notify("server_full")
        elif new_state == JoinState.SUCCESS:
            self._notifier.notify("success")

    def _on_success(self) -> None:
        """Handle successful join."""
        self._stop("Successfully joined server!")

    def _update_status(self, color_key: str, text: str) -> None:
        """Update the status display.

        Args:
            color_key: Key for status color.
            text: Status text.
        """
        color = STATUS_COLORS.get(color_key, STATUS_COLORS["idle"])
        self._status_text.configure(text=text, text_color=color)
        self._status_indicator.configure(text_color=color)

    def _log(self, message: str) -> None:
        """Add a message to the activity log.

        Args:
            message: Message to log.
        """
        # Thread-safe logging
        self.after(0, lambda: self._activity_log.log(message))

    def _open_settings(self) -> None:
        """Open settings popup."""
        SettingsPopup(self, self._config, self._on_settings_save)

    def _on_settings_save(self, new_config: dict) -> None:
        """Handle settings save.

        Args:
            new_config: New configuration.
        """
        self._config = new_config
        self._save_config()

        # Update notifier
        self._notifier.set_sound_enabled(self._config.get("sound_enabled", True))
        self._notifier.set_discord_webhook(self._config.get("discord_webhook_url") or None)

        # Update state machine config if running
        if self._state_machine:
            self._state_machine.config.timeout_seconds = self._config.get("timeout_seconds", 15.0)

        self._log("Settings saved")

    def _on_quit(self) -> None:
        """Handle quit."""
        self._stop("Application closing")

        # Cleanup
        if self._screen_capture:
            self._screen_capture.cleanup()

        # Remove hotkeys
        try:
            keyboard.remove_hotkey("F6")
            keyboard.remove_hotkey("F7")
        except (KeyError, ValueError):
            pass

        self.destroy()

    def run(self) -> None:
        """Run the application."""
        self.mainloop()


def main():
    """Main entry point."""
    print("Ark JoinSim v4")
    print("-" * 40)

    # Check dependencies
    missing = []

    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")

    try:
        import keyboard
    except ImportError:
        missing.append("keyboard")

    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")

    try:
        import mss
    except ImportError:
        missing.append("mss")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Run: pip install {' '.join(missing)}")
        return

    # Run app
    app = JoinSimApp()
    app.run()


if __name__ == "__main__":
    main()
