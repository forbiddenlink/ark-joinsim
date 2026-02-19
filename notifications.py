"""
Notifications module for Ark JoinSim.

Provides Discord webhook notifications and sound alerts for various events.
Supports Windows sound via winsound with graceful fallback for other platforms.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

# Try to import winsound for Windows sound support
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class Notifier:
    """
    Handles notifications for Ark JoinSim events.

    Supports Discord webhook notifications and sound alerts.
    Sound alerts use winsound on Windows with graceful degradation on other platforms.
    """

    # Discord embed colors for different event types
    COLORS = {
        'success': 0x00FF00,      # Green
        'server_full': 0xFFFF00,  # Yellow
        'error': 0xFF0000,        # Red
        'start': 0x0099FF,        # Blue
        'stop': 0x888888,         # Gray
        'limit_reached': 0xFF8800 # Orange
    }

    # Sound definitions: list of (frequency_hz, duration_ms) tuples
    SOUNDS = {
        'start': [(800, 200)],
        'stop': [(400, 200)],
        'success': [(1000, 150), (1200, 150), (1400, 150)],  # Ascending triple beep
        'server_full': [(600, 200), (600, 200)],             # Double beep
        'error': [(500, 150), (400, 150), (300, 150)],       # Descending
        'limit_reached': [(1000, 150), (1200, 150), (1000, 150)]
    }

    # Default messages for event types
    DEFAULT_MESSAGES = {
        'start': 'JoinSim started',
        'stop': 'JoinSim stopped',
        'success': 'Successfully joined server!',
        'server_full': 'Server is full, retrying...',
        'error': 'An error occurred',
        'limit_reached': 'Click limit reached'
    }

    def __init__(self):
        """Initialize the Notifier with default settings."""
        self._discord_webhook_url: Optional[str] = None
        self._sound_enabled: bool = True

    def set_discord_webhook(self, url: Optional[str]) -> None:
        """
        Configure the Discord webhook URL.

        Args:
            url: Discord webhook URL, or None to disable Discord notifications.
        """
        self._discord_webhook_url = url

    def set_sound_enabled(self, enabled: bool) -> None:
        """
        Toggle sound notifications.

        Args:
            enabled: True to enable sounds, False to disable.
        """
        self._sound_enabled = enabled

    def play_sound(self, sound_type: str) -> bool:
        """
        Play a sound for the specified event type.

        Args:
            sound_type: One of 'start', 'stop', 'success', 'server_full',
                       'error', or 'limit_reached'.

        Returns:
            True if sound was played, False if sounds are disabled or unavailable.
        """
        if not self._sound_enabled:
            return False

        if not HAS_WINSOUND:
            return False

        sound_sequence = self.SOUNDS.get(sound_type)
        if not sound_sequence:
            return False

        try:
            for frequency, duration in sound_sequence:
                winsound.Beep(frequency, duration)
            return True
        except Exception:
            # Beep can fail in some environments (e.g., no audio device)
            return False

    def _send_discord_notification(self, event_type: str, message: str) -> bool:
        """
        Send a notification to Discord via webhook.

        Args:
            event_type: The type of event for color selection.
            message: The message to send.

        Returns:
            True if notification was sent successfully, False otherwise.
        """
        if not self._discord_webhook_url:
            return False

        color = self.COLORS.get(event_type, 0x888888)
        timestamp = datetime.now(timezone.utc).isoformat()

        payload = {
            "embeds": [{
                "title": "\U0001F996 Ark JoinSim",  # Dinosaur emoji
                "description": message,
                "color": color,
                "timestamp": timestamp
            }]
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            request = urllib.request.Request(
                self._discord_webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status == 204 or response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, Exception):
            # Don't crash on webhook failures
            return False

    def notify(self, event_type: str, message: Optional[str] = None) -> dict:
        """
        Send a notification for the specified event.

        Sends both Discord webhook notification (if configured) and plays
        a sound (if enabled and available on Windows).

        Args:
            event_type: One of 'start', 'stop', 'success', 'server_full',
                       'error', or 'limit_reached'.
            message: Optional custom message. If None, uses default message
                    for the event type.

        Returns:
            Dict with 'sound' and 'discord' keys indicating success/failure
            of each notification type.
        """
        if message is None:
            message = self.DEFAULT_MESSAGES.get(event_type, event_type)

        result = {
            'sound': self.play_sound(event_type),
            'discord': self._send_discord_notification(event_type, message)
        }

        return result
