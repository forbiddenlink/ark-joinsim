"""
Join State Machine for ARK Server Auto-Join Bot.

Manages the state transitions for the auto-join process, tracking
retries, timeouts, and providing callbacks for state changes.
"""

import time
import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple, Dict, Any, List


class JoinState(Enum):
    """States for the join state machine."""
    IDLE = auto()           # Bot stopped, waiting for user
    SEARCHING = auto()      # Looking for ARK window + Join button
    CLICKING = auto()       # Found target, performing click
    WAITING = auto()        # Clicked, waiting for result (max 15s)
    SUCCESS = auto()        # Joined server successfully
    FAILED_FULL = auto()    # Server full popup detected
    FAILED_TIMEOUT = auto() # Stuck too long or kicked to server list
    RETRY = auto()          # Preparing to retry (wait 1-3s then back to SEARCHING)


@dataclass
class StateMachineConfig:
    """Configuration for the join state machine."""
    timeout_seconds: float = 15.0       # Max time to wait after clicking
    retry_delay_min: float = 1.0        # Minimum retry delay in seconds
    retry_delay_max: float = 3.0        # Maximum retry delay in seconds
    max_retries: int = 0                # 0 = unlimited retries
    window_timeout: float = 10.0        # Time to wait for window before going IDLE


@dataclass
class StateInfo:
    """Information about the current state machine state."""
    current_state: JoinState
    time_in_state: float
    retry_count: int
    total_clicks: int
    start_time: Optional[float]
    last_error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert state info to dictionary."""
        return {
            'current_state': self.current_state.name,
            'time_in_state': round(self.time_in_state, 2),
            'retry_count': self.retry_count,
            'total_clicks': self.total_clicks,
            'start_time': self.start_time,
            'last_error': self.last_error,
        }


class JoinStateMachine:
    """
    State machine for managing ARK server join attempts.

    Handles state transitions based on detection results from the screen
    analyzer, manages retries, and provides callbacks for state changes.

    Example usage:
        sm = JoinStateMachine()
        sm.on_state_change(lambda old, new: print(f"{old.name} -> {new.name}"))
        sm.start()

        # In main loop:
        detections = {
            'window_found': True,
            'join_button': (100, 200),
            'server_full': False,
            'server_list': False,
            'loading': False,
            'spawn_screen': False,
        }
        action = sm.update(detections)
    """

    def __init__(self, config: Optional[StateMachineConfig] = None):
        """
        Initialize the state machine.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or StateMachineConfig()
        self._state = JoinState.IDLE
        self._state_enter_time = time.time()
        self._retry_count = 0
        self._total_clicks = 0
        self._start_time: Optional[float] = None
        self._last_error: Optional[str] = None
        self._callbacks: List[Callable[[JoinState, JoinState], None]] = []
        self._retry_target_time: Optional[float] = None
        self._pending_click_position: Optional[Tuple[int, int]] = None
        self._window_lost_time: Optional[float] = None

    def _transition_to(self, new_state: JoinState, error: Optional[str] = None) -> None:
        """
        Transition to a new state.

        Args:
            new_state: The state to transition to.
            error: Optional error message to record.
        """
        if new_state == self._state:
            return

        old_state = self._state
        self._state = new_state
        self._state_enter_time = time.time()

        if error:
            self._last_error = error

        # Reset state-specific tracking
        if new_state == JoinState.RETRY:
            delay = random.uniform(self.config.retry_delay_min, self.config.retry_delay_max)
            self._retry_target_time = time.time() + delay
            self._pending_click_position = None  # Clear stale click position
        elif new_state == JoinState.SEARCHING:
            self._window_lost_time = None
            self._pending_click_position = None  # Clear stale click position
        elif new_state == JoinState.IDLE:
            self._retry_target_time = None
            self._window_lost_time = None
            self._pending_click_position = None  # Clear stale click position
        elif new_state in (JoinState.SUCCESS, JoinState.FAILED_FULL, JoinState.FAILED_TIMEOUT):
            self._pending_click_position = None  # Clear stale click position

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(old_state, new_state)
            except Exception:
                pass  # Don't let callback errors break state machine

    def start(self) -> bool:
        """
        Start the state machine from IDLE.

        Returns:
            True if successfully started, False if not in IDLE state.
        """
        if self._state != JoinState.IDLE:
            return False

        self._start_time = time.time()
        self._retry_count = 0
        self._total_clicks = 0
        self._last_error = None
        self._transition_to(JoinState.SEARCHING)
        return True

    def stop(self) -> None:
        """Stop the state machine and return to IDLE from any state."""
        self._transition_to(JoinState.IDLE)

    def get_state(self) -> JoinState:
        """
        Get the current state.

        Returns:
            Current JoinState enum value.
        """
        return self._state

    def get_state_info(self) -> StateInfo:
        """
        Get detailed information about the current state.

        Returns:
            StateInfo dataclass with current state details.
        """
        return StateInfo(
            current_state=self._state,
            time_in_state=time.time() - self._state_enter_time,
            retry_count=self._retry_count,
            total_clicks=self._total_clicks,
            start_time=self._start_time,
            last_error=self._last_error,
        )

    def on_state_change(self, callback: Callable[[JoinState, JoinState], None]) -> None:
        """
        Register a callback for state changes.

        Args:
            callback: Function that takes (old_state, new_state) as arguments.
        """
        self._callbacks.append(callback)

    def remove_state_change_callback(self, callback: Callable[[JoinState, JoinState], None]) -> bool:
        """
        Remove a previously registered callback.

        Args:
            callback: The callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        try:
            self._callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def get_pending_click(self) -> Optional[Tuple[int, int]]:
        """
        Get and clear the pending click position.

        Returns:
            Click position (x, y) if a click is pending, None otherwise.
        """
        pos = self._pending_click_position
        self._pending_click_position = None
        return pos

    def update(self, detections: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Update the state machine based on detection results.

        This is the main update loop method. Call this regularly with
        fresh detection results to drive state transitions.

        Args:
            detections: Dictionary with detection results:
                - window_found: bool - ARK window is visible
                - join_button: (x, y) or None - Position of join button
                - server_full: bool - Server full popup detected
                - server_list: bool - Server list screen detected
                - loading: bool - Loading screen detected
                - spawn_screen: bool - Spawn/game screen detected

        Returns:
            Action string or None:
                - 'click' - Caller should click at get_pending_click() position
                - 'dismiss_popup' - Caller should dismiss server full popup
                - None - No action needed
        """
        # Handle None detections gracefully
        if detections is None:
            detections = {}

        window_found = detections.get('window_found', False)
        join_button = detections.get('join_button')
        server_full = detections.get('server_full', False)
        server_list = detections.get('server_list', False)
        loading = detections.get('loading', False)
        spawn_screen = detections.get('spawn_screen', False)

        action = None

        if self._state == JoinState.IDLE:
            # Do nothing, waiting for start()
            pass

        elif self._state == JoinState.SEARCHING:
            if not window_found:
                # Track how long window has been missing
                if self._window_lost_time is None:
                    self._window_lost_time = time.time()
                elif time.time() - self._window_lost_time >= self.config.window_timeout:
                    self._transition_to(JoinState.IDLE, error="Window not found")
            else:
                self._window_lost_time = None
                if join_button is not None:
                    # Found join button, transition to clicking
                    self._pending_click_position = join_button
                    self._transition_to(JoinState.CLICKING)

        elif self._state == JoinState.CLICKING:
            # Perform click and transition to waiting
            if self._pending_click_position:
                action = 'click'
                self._total_clicks += 1
                self._transition_to(JoinState.WAITING)
            else:
                # No click position available, go back to searching
                self._transition_to(JoinState.SEARCHING, error="No click position available")

        elif self._state == JoinState.WAITING:
            time_in_state = time.time() - self._state_enter_time

            # Check for success conditions
            if loading or spawn_screen:
                self._transition_to(JoinState.SUCCESS)

            # Check for server full popup
            elif server_full:
                self._transition_to(JoinState.FAILED_FULL, error="Server full")

            # Check for timeout or kicked back to server list
            elif time_in_state >= self.config.timeout_seconds:
                self._transition_to(JoinState.FAILED_TIMEOUT, error="Timeout waiting for result")
            elif server_list and time_in_state > 2.0:
                # If we see server list after waiting a bit, we got kicked
                self._transition_to(JoinState.FAILED_TIMEOUT, error="Kicked to server list")

        elif self._state == JoinState.SUCCESS:
            # Stay in success until stop() is called
            pass

        elif self._state == JoinState.FAILED_FULL:
            # Need to dismiss popup and retry
            action = 'dismiss_popup'
            self._retry_count += 1

            # Check max retries
            if self.config.max_retries > 0 and self._retry_count >= self.config.max_retries:
                self._transition_to(JoinState.IDLE, error="Max retries reached")
            else:
                self._transition_to(JoinState.RETRY)

        elif self._state == JoinState.FAILED_TIMEOUT:
            # Retry after timeout
            self._retry_count += 1

            # Check max retries
            if self.config.max_retries > 0 and self._retry_count >= self.config.max_retries:
                self._transition_to(JoinState.IDLE, error="Max retries reached")
            else:
                self._transition_to(JoinState.RETRY)

        elif self._state == JoinState.RETRY:
            # Wait for retry delay, then go back to searching
            if self._retry_target_time is None:
                # Defensive: if no target time set, retry immediately
                self._transition_to(JoinState.SEARCHING)
            elif time.time() >= self._retry_target_time:
                self._transition_to(JoinState.SEARCHING)

        return action

    def reset_stats(self) -> None:
        """Reset retry count and click statistics without changing state."""
        self._retry_count = 0
        self._total_clicks = 0
        self._last_error = None

    def __repr__(self) -> str:
        """String representation for debugging."""
        info = self.get_state_info()
        return (
            f"JoinStateMachine(state={info.current_state.name}, "
            f"time_in_state={info.time_in_state:.1f}s, "
            f"retries={info.retry_count}, clicks={info.total_clicks})"
        )
