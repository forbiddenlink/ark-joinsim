"""
Human-like input simulation module for Ark JoinSim.

Provides realistic mouse movement and clicking behavior to avoid detection.
Uses Bezier curves for movement, Gaussian timing distributions, and micro-jitter.

Features:
- Bezier curve mouse movement (more human-like than linear)
- Gaussian timing distribution instead of uniform random
- Micro-jitter during click hold
- Position jitter around target
- Configurable click duration

Platform Support:
- Windows: Uses pydirectinput for better DirectX game support
- macOS/Linux: Falls back to pyautogui
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

# Thread lock for input operations
_input_lock = threading.Lock()

# Input backend detection
_BACKEND: str = "none"
_input_module = None
_has_pyautogui = False

# Try pydirectinput first (Windows + better DirectX support)
try:
    import pydirectinput
    _input_module = pydirectinput
    _BACKEND = "pydirectinput"
    # pydirectinput doesn't have FAILSAFE, but we'll handle it ourselves
except ImportError:
    pass

# Fall back to pyautogui
if _input_module is None:
    try:
        import pyautogui
        _input_module = pyautogui
        _BACKEND = "pyautogui"
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01  # Minimal pause, we handle timing ourselves
        _has_pyautogui = True
    except ImportError:
        pass

# For screen size detection, pyautogui is always preferred
try:
    import pyautogui as _pyautogui_screen
    _has_pyautogui = True
except ImportError:
    _pyautogui_screen = None


def get_backend() -> str:
    """Return the current input backend name."""
    return _BACKEND


def is_available() -> bool:
    """Check if any input backend is available."""
    return _input_module is not None


@dataclass
class HumanInputConfig:
    """Configuration for human-like input behavior."""

    # Position jitter (pixels to vary around target)
    position_jitter: int = 5

    # Click duration range (seconds)
    click_duration_min: float = 0.05
    click_duration_max: float = 0.15

    # Movement speed factor (lower = faster, higher = slower)
    movement_speed: float = 1.0

    # Bezier curve control point variance (how curved the path is)
    curve_variance: float = 0.3

    # Enable micro-jitter during click hold
    micro_jitter_enabled: bool = True
    micro_jitter_pixels: int = 2
    micro_jitter_interval: float = 0.02

    # Gaussian delay parameters
    delay_mean: float = 0.05
    delay_stddev: float = 0.02
    delay_min: float = 0.01

    # Movement steps (more = smoother but slower)
    movement_steps_min: int = 20
    movement_steps_max: int = 40


class HumanInput:
    """
    Handles mouse and keyboard input with human-like behavior.

    Uses Bezier curves for mouse movement, Gaussian timing distributions,
    and micro-jitter to simulate realistic human input patterns.

    Thread-safe: All input operations are protected by a lock.

    Example:
        input_handler = HumanInput()
        input_handler.click(500, 300)  # Human-like click at position
        input_handler.press_key('escape')  # Press ESC key
    """

    def __init__(self, config: Optional[HumanInputConfig] = None):
        """
        Initialize the human input handler.

        Args:
            config: Optional configuration. Uses defaults if not provided.

        Raises:
            RuntimeError: If no input backend is available.
        """
        if not is_available():
            raise RuntimeError(
                "No input backend available. Install pydirectinput (Windows) "
                "or pyautogui: pip install pydirectinput pyautogui"
            )

        self.config = config or HumanInputConfig()
        self._screen_size: Optional[Tuple[int, int]] = None

    @property
    def screen_size(self) -> Tuple[int, int]:
        """Get the screen size, caching the result."""
        if self._screen_size is None:
            self._screen_size = self._get_screen_size()
        return self._screen_size

    def _get_screen_size(self) -> Tuple[int, int]:
        """Get the current screen size."""
        if _has_pyautogui and _pyautogui_screen is not None:
            return _pyautogui_screen.size()
        # Fallback: common resolution
        return (1920, 1080)

    def _clamp_position(self, x: int, y: int) -> Tuple[int, int]:
        """Clamp position to screen bounds."""
        width, height = self.screen_size
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        return (x, y)

    def _is_on_screen(self, x: int, y: int) -> bool:
        """Check if position is within screen bounds."""
        width, height = self.screen_size
        return 0 <= x < width and 0 <= y < height

    def gaussian_delay(
        self,
        mean: Optional[float] = None,
        stddev: Optional[float] = None,
        min_val: Optional[float] = None
    ) -> float:
        """
        Generate a random delay using Gaussian distribution.

        More realistic than uniform random - clusters around mean value
        with occasional longer/shorter delays.

        Args:
            mean: Mean delay in seconds (default from config)
            stddev: Standard deviation (default from config)
            min_val: Minimum value (default from config)

        Returns:
            Random delay in seconds, guaranteed >= min_val
        """
        mean = mean if mean is not None else self.config.delay_mean
        stddev = stddev if stddev is not None else self.config.delay_stddev
        min_val = min_val if min_val is not None else self.config.delay_min

        delay = random.gauss(mean, stddev)
        return max(min_val, delay)

    def _bezier_point(
        self,
        t: float,
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float]
    ) -> Tuple[float, float]:
        """
        Calculate a point on a cubic Bezier curve.

        Args:
            t: Parameter 0-1 along the curve
            p0, p1, p2, p3: Control points

        Returns:
            (x, y) point on the curve
        """
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0[0]
        x += 3 * uu * t * p1[0]
        x += 3 * u * tt * p2[0]
        x += ttt * p3[0]

        y = uuu * p0[1]
        y += 3 * uu * t * p1[1]
        y += 3 * u * tt * p2[1]
        y += ttt * p3[1]

        return (x, y)

    def _generate_bezier_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        steps: int
    ) -> list[Tuple[int, int]]:
        """
        Generate a Bezier curve path from start to end.

        Args:
            start: Starting position (x, y)
            end: Ending position (x, y)
            steps: Number of points along the path

        Returns:
            List of (x, y) positions along the curve
        """
        # Calculate distance for control point variance
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Generate random control points for curve variance
        variance = self.config.curve_variance * distance

        # Control point 1: offset from start towards end
        cp1_x = start[0] + dx * 0.3 + random.uniform(-variance, variance)
        cp1_y = start[1] + dy * 0.3 + random.uniform(-variance, variance)

        # Control point 2: offset from end towards start
        cp2_x = start[0] + dx * 0.7 + random.uniform(-variance, variance)
        cp2_y = start[1] + dy * 0.7 + random.uniform(-variance, variance)

        p0 = (float(start[0]), float(start[1]))
        p1 = (cp1_x, cp1_y)
        p2 = (cp2_x, cp2_y)
        p3 = (float(end[0]), float(end[1]))

        path = []
        for i in range(steps + 1):
            t = i / steps
            point = self._bezier_point(t, p0, p1, p2, p3)
            # Round to integers and clamp to screen
            x, y = self._clamp_position(int(round(point[0])), int(round(point[1])))
            path.append((x, y))

        return path

    def _get_current_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        if _has_pyautogui and _pyautogui_screen is not None:
            pos = _pyautogui_screen.position()
            return (pos[0], pos[1])
        # Fallback: assume center of screen
        w, h = self.screen_size
        return (w // 2, h // 2)

    def move_to(self, x: int, y: int, duration: Optional[float] = None) -> None:
        """
        Move mouse to target position using Bezier curve.

        Creates a natural-looking curved path instead of a straight line.
        Movement speed varies slightly to appear more human.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            duration: Optional movement duration (auto-calculated if not provided)

        Thread-safe: Uses lock to prevent concurrent movements.
        """
        if not self._is_on_screen(x, y):
            x, y = self._clamp_position(x, y)

        with _input_lock:
            start = self._get_current_position()

            # Calculate distance for duration and steps
            dx = x - start[0]
            dy = y - start[1]
            distance = math.sqrt(dx * dx + dy * dy)

            # Auto-calculate duration based on distance if not provided
            if duration is None:
                # Base: ~0.1s per 100 pixels, scaled by movement_speed
                duration = (distance / 1000.0) * self.config.movement_speed
                duration = max(0.05, min(0.5, duration))  # Clamp to reasonable range
                # Add slight random variance
                duration *= random.uniform(0.9, 1.1)

            # Calculate steps based on duration
            steps = int(
                self.config.movement_steps_min +
                (self.config.movement_steps_max - self.config.movement_steps_min) *
                min(1.0, distance / 500.0)
            )

            # Generate path
            path = self._generate_bezier_path(start, (x, y), steps)

            # Calculate time per step with variance
            step_delay = duration / len(path)

            # Execute movement
            for point in path:
                try:
                    if _BACKEND == "pydirectinput":
                        _input_module.moveTo(point[0], point[1])
                    else:
                        _input_module.moveTo(point[0], point[1], _pause=False)
                except Exception:
                    # Silently continue on minor errors
                    pass

                # Variable delay between steps (more human-like)
                actual_delay = step_delay * random.uniform(0.8, 1.2)
                time.sleep(max(0.001, actual_delay))

    def _perform_micro_jitter(self, center_x: int, center_y: int, duration: float) -> None:
        """
        Perform subtle micro-movements during click hold.

        Humans can't hold perfectly still - this simulates that behavior.

        Args:
            center_x: Center X position
            center_y: Center Y position
            duration: How long to jitter for
        """
        if not self.config.micro_jitter_enabled:
            time.sleep(duration)
            return

        pixels = self.config.micro_jitter_pixels
        interval = self.config.micro_jitter_interval
        elapsed = 0.0

        while elapsed < duration:
            # Small random offset
            jx = center_x + random.randint(-pixels, pixels)
            jy = center_y + random.randint(-pixels, pixels)
            jx, jy = self._clamp_position(jx, jy)

            try:
                if _BACKEND == "pydirectinput":
                    _input_module.moveTo(jx, jy)
                else:
                    _input_module.moveTo(jx, jy, _pause=False)
            except Exception:
                pass

            sleep_time = min(interval, duration - elapsed)
            time.sleep(sleep_time)
            elapsed += interval

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        move_first: bool = True
    ) -> None:
        """
        Perform a human-like click at the specified position.

        Includes:
        - Position jitter (slight offset from exact target)
        - Bezier curve movement to position
        - Pre-click delay (humans don't click instantly after moving)
        - Click hold duration (not instant press/release)
        - Micro-jitter during hold

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            button: Mouse button ('left', 'right', 'middle')
            move_first: Whether to move to position before clicking

        Thread-safe: Uses lock to prevent concurrent operations.
        """
        # Apply position jitter
        jitter = self.config.position_jitter
        target_x = x + random.randint(-jitter, jitter)
        target_y = y + random.randint(-jitter, jitter)
        target_x, target_y = self._clamp_position(target_x, target_y)

        with _input_lock:
            # Move to position
            if move_first:
                # Release lock temporarily for movement (which has its own lock)
                pass

        # Movement is outside the main lock since it acquires its own
        if move_first:
            self.move_to(target_x, target_y)

        with _input_lock:
            # Pre-click delay (humans pause briefly before clicking)
            pre_delay = self.gaussian_delay(mean=0.04, stddev=0.02, min_val=0.01)
            time.sleep(pre_delay)

            # Calculate hold duration
            hold_duration = random.uniform(
                self.config.click_duration_min,
                self.config.click_duration_max
            )

            # Press mouse button
            try:
                if _BACKEND == "pydirectinput":
                    _input_module.mouseDown(button=button)
                else:
                    _input_module.mouseDown(button=button, _pause=False)
            except Exception as e:
                # Log but continue
                pass

            # Hold with micro-jitter
            self._perform_micro_jitter(target_x, target_y, hold_duration)

            # Release mouse button
            try:
                if _BACKEND == "pydirectinput":
                    _input_module.mouseUp(button=button)
                else:
                    _input_module.mouseUp(button=button, _pause=False)
            except Exception:
                pass

            # Small post-click delay
            post_delay = self.gaussian_delay(mean=0.02, stddev=0.01, min_val=0.005)
            time.sleep(post_delay)

    def press_key(self, key: str, hold_duration: Optional[float] = None) -> None:
        """
        Press and release a keyboard key with human-like timing.

        Args:
            key: Key to press (e.g., 'escape', 'enter', 'space', 'a')
            hold_duration: Optional hold duration (random if not provided)

        Thread-safe: Uses lock to prevent concurrent operations.
        """
        with _input_lock:
            # Calculate hold duration
            if hold_duration is None:
                hold_duration = self.gaussian_delay(mean=0.08, stddev=0.03, min_val=0.03)

            try:
                if _BACKEND == "pydirectinput":
                    _input_module.keyDown(key)
                    time.sleep(hold_duration)
                    _input_module.keyUp(key)
                else:
                    _input_module.keyDown(key, _pause=False)
                    time.sleep(hold_duration)
                    _input_module.keyUp(key, _pause=False)
            except Exception:
                # Some keys might not be supported
                pass

            # Post-key delay
            time.sleep(self.gaussian_delay(mean=0.03, stddev=0.01, min_val=0.01))

    def double_click(self, x: int, y: int, button: str = "left") -> None:
        """
        Perform a human-like double-click.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            button: Mouse button ('left', 'right', 'middle')
        """
        # First click with movement
        self.click(x, y, button=button, move_first=True)

        # Short delay between clicks (typical double-click timing)
        delay = self.gaussian_delay(mean=0.08, stddev=0.02, min_val=0.04)
        time.sleep(delay)

        # Second click without movement (same position)
        self.click(x, y, button=button, move_first=False)


# Module-level convenience functions
_default_handler: Optional[HumanInput] = None


def get_handler() -> HumanInput:
    """Get or create the default HumanInput handler."""
    global _default_handler
    if _default_handler is None:
        _default_handler = HumanInput()
    return _default_handler


def click(x: int, y: int, button: str = "left") -> None:
    """Convenience function for human-like click."""
    get_handler().click(x, y, button)


def move_to(x: int, y: int) -> None:
    """Convenience function for Bezier curve movement."""
    get_handler().move_to(x, y)


def press_key(key: str) -> None:
    """Convenience function for human-like key press."""
    get_handler().press_key(key)


if __name__ == "__main__":
    # Simple test/demo
    print(f"Input backend: {get_backend()}")
    print(f"Available: {is_available()}")

    if is_available():
        handler = HumanInput()
        print(f"Screen size: {handler.screen_size}")
        print(f"Current position: {handler._get_current_position()}")

        # Demo: move mouse in a small pattern
        print("\nDemo: Moving mouse...")
        x, y = handler._get_current_position()
        handler.move_to(x + 100, y)
        time.sleep(0.2)
        handler.move_to(x + 100, y + 100)
        time.sleep(0.2)
        handler.move_to(x, y + 100)
        time.sleep(0.2)
        handler.move_to(x, y)
        print("Demo complete!")
