# JoinSim v4 Design: Smart Detection + Auto-Retry

**Date:** 2026-02-19
**Status:** Approved
**Goal:** Detect join failures (server full, timeout) and automatically retry. Auto-find ARK window. Modern UI.

---

## Problem Statement

Current JoinSim v3 is a "blind clicker" - it clicks the Join button repeatedly but has no idea if:
- The join succeeded (player entered the server)
- The join failed (server full popup appeared)
- The player got kicked back to the server list

The bot gets stuck because it doesn't detect these states. Other bots handle this better.

---

## Success Criteria

1. **Detects "Server Full" popup** and dismisses it automatically
2. **Detects "kicked back to server list"** and clicks Join again
3. **Detects successful join** (loading screen / spawn screen) and stops
4. **Auto-finds ARK window** - no manual position setting required
5. **Works at any resolution** via multi-scale template matching
6. **Modern, polished UI** that looks professional
7. **Better than competing bots** in reliability and features

---

## Architecture

### State Machine

```
IDLE → SEARCHING → CLICKING → WAITING → SUCCESS
                      ↓           ↓
                   RETRY ← FAILED_FULL
                      ↑           ↓
                      ← FAILED_TIMEOUT
```

**States:**
| State | Description | Action |
|-------|-------------|--------|
| IDLE | Bot stopped | Wait for user to start |
| SEARCHING | Looking for ARK window + Join button | Capture screen, run detection |
| CLICKING | Found target, clicking | Click with human-like behavior |
| WAITING | Clicked, waiting for result | Monitor for loading/popup/server list |
| SUCCESS | Joined server | Stop bot, notify user |
| FAILED_FULL | Server full popup detected | Dismiss popup, transition to RETRY |
| FAILED_TIMEOUT | Stuck >15s or kicked to server list | Transition to RETRY |
| RETRY | Preparing to try again | Wait 1-3s, transition to SEARCHING |

### Detection Loop (runs every 500ms)

```python
def detection_loop():
    while running:
        frame = capture_screen()

        if state == WAITING:
            if detect('loading_screen'):
                # Join in progress, keep waiting
                pass
            elif detect('server_full_popup'):
                state = FAILED_FULL
                dismiss_popup()
            elif detect('server_list'):
                # Kicked back
                state = FAILED_TIMEOUT
            elif detect('spawn_screen') or detect('hud'):
                state = SUCCESS
                stop_bot()
            elif time_in_state > 15:
                state = FAILED_TIMEOUT

        elif state == SEARCHING:
            if detect('join_button'):
                state = CLICKING
                click_target()

        sleep(0.5)
```

---

## UI Design

### Main Window (CustomTkinter Dark Theme)

```
┌─────────────────────────────────────────────────┐
│  🦖 Ark JoinSim v4                        [—][×]│
├─────────────────────────────────────────────────┤
│                                                 │
│         ●  READY TO JOIN                        │
│         (Large color-coded status)              │
│                                                 │
├─────────────────────────────────────────────────┤
│  Detection Status                               │
│  ├─ ARK Window:     ✓ Found (1920x1080)        │
│  ├─ Join Button:    ✓ Located                  │
│  ├─ Server Full:    Not visible                │
│  └─ Loading:        Not visible                │
├─────────────────────────────────────────────────┤
│  Session Stats                                  │
│  ├─ Retry Count:    0                          │
│  ├─ Time Elapsed:   0:00                       │
│  └─ Success Rate:   --                         │
├─────────────────────────────────────────────────┤
│                                                 │
│   ┌──────────────┐    ┌──────────────┐         │
│   │   ▶ START    │    │  ⚙ Settings  │         │
│   └──────────────┘    └──────────────┘         │
│                                                 │
├─────────────────────────────────────────────────┤
│  Activity Log                             [^]   │
│  ┌─────────────────────────────────────────┐   │
│  │ 10:23:01  Searching for ARK window...   │   │
│  │ 10:23:02  Found ARK window              │   │
│  │ 10:23:02  Join button located           │   │
│  │ 10:23:03  Clicking join...              │   │
│  │ 10:23:05  Server full, retrying...      │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Status Colors

| Status | Color | Indicator |
|--------|-------|-----------|
| Stopped/Idle | Gray | ⏹ |
| Searching | Blue | 🔍 |
| Clicking/Active | Green | 🟢 |
| Waiting | Yellow | ⏳ |
| Error/Failed | Red | ❌ |
| Success | Bright Green | ✓ |

### Settings Panel (Collapsible)

- Click interval (default 2.5s)
- Timeout threshold (default 15s)
- Sound notifications toggle
- Discord webhook URL (optional)
- Recapture templates button

---

## Template Capture (First-Time Setup)

### Setup Wizard Flow

1. **Welcome screen** - Explains what templates are needed
2. **Step 1: Join Button** - User hovers over Join button, presses F8
3. **Step 2: Server Full Popup** - User triggers a full server, captures popup
4. **Step 3: Server List** - User captures any part of the server browser
5. **Step 4: Loading Screen** (optional) - Helps detect join in progress
6. **Complete** - Templates saved, ready to use

### Template Storage

```
templates/
├── join_button_1920x1080.png
├── server_full_1920x1080.png
├── server_list_1920x1080.png
├── loading_1920x1080.png
└── manifest.json  # Maps resolution to templates
```

### Resolution Handling

1. **Multi-scale matching** - Templates work at different resolutions by scaling
2. **Resolution-specific templates** - If multi-scale fails, prompt recapture
3. **Manifest tracks** which resolutions have been captured

---

## Detection System

### Primary Method: Multi-Scale Template Matching

```python
def find_template(image, template, threshold=0.8):
    for scale in np.linspace(0.5, 1.5, 15):
        resized = cv2.resize(image, scale)
        edges = cv2.Canny(resized, 50, 200)
        result = cv2.matchTemplate(edges, template_edges, TM_CCOEFF_NORMED)
        if max(result) > threshold:
            return location
    return None
```

### Fallback Chain

If primary detection fails, try in order:
1. **Exact template match** (fastest)
2. **Multi-scale with edge detection** (handles resolution)
3. **HSV color filtering** (handles overlays)
4. **Feature matching (ORB)** (slowest, most robust)

### Screen Capture

| Platform | Library | FPS | Notes |
|----------|---------|-----|-------|
| Windows | DXcam | 240+ | Best performance, DirectX support |
| Windows (fallback) | MSS | 30-60 | If DXcam fails |
| Mac/Linux | MSS | 30-60 | Cross-platform |

### Window Detection

```python
# Windows
import win32gui
def find_ark_window():
    def callback(hwnd, windows):
        if "ARK: Survival Ascended" in win32gui.GetWindowText(hwnd):
            windows.append(hwnd)
    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows[0] if windows else None

# Cross-platform fallback
import pygetwindow
def find_ark_window():
    windows = pygetwindow.getWindowsWithTitle("ARK: Survival Ascended")
    return windows[0] if windows else None
```

---

## Input Simulation

### Improvements Over v3

| Feature | v3 | v4 |
|---------|----|----|
| Input library | pyautogui | pydirectinput (Windows) |
| Mouse movement | Linear | Bezier curves |
| Timing distribution | Uniform random | Gaussian distribution |
| Click hold | Static hold | Micro-jitter during hold |

### Bezier Mouse Movement

```python
from pyclick import HumanCurve

def human_move_to(x, y):
    current = pyautogui.position()
    curve = HumanCurve(current, (x, y), distortion_mean=1.5)
    for point in curve.points:
        pydirectinput.moveTo(int(point[0]), int(point[1]))
        time.sleep(0.001)
```

### Gaussian Timing

```python
import random

def gaussian_delay(mean=2.5, stddev=0.5, min_val=0.5):
    delay = random.gauss(mean, stddev)
    return max(min_val, delay)
```

---

## Notifications

### Discord Webhook

```python
import requests

def send_discord_notification(webhook_url, message, color=0x00ff00):
    payload = {
        "embeds": [{
            "title": "🦖 Ark JoinSim",
            "description": message,
            "color": color
        }]
    }
    requests.post(webhook_url, json=payload)
```

**Events to notify:**
- Join successful (green)
- Server full, retrying (yellow)
- Error / bot stopped (red)
- Click limit reached (blue)

### Sound Notifications

| Event | Sound |
|-------|-------|
| Start | 800Hz beep |
| Stop/Pause | 400Hz beep |
| Success | Triple ascending beep |
| Server full | Double beep |
| Error | Descending tone |

---

## File Structure

```
ark-joinsim/
├── joinsim.py              # Main app entry point + UI
├── vision.py               # Screen capture + template matching
├── input_handler.py        # Mouse/keyboard with human-like behavior
├── state_machine.py        # Join state tracking
├── notifications.py        # Discord webhooks + sounds
├── setup_wizard.py         # First-time template capture UI
├── templates/              # User-captured templates
│   └── manifest.json
├── docs/
│   └── plans/
│       └── 2026-02-19-joinsim-v4-design.md
├── requirements.txt
├── joinsim_config.json
└── README.md
```

---

## Dependencies

```
# UI
customtkinter>=5.0.0

# Vision
opencv-python>=4.8.0
numpy>=1.24.0
mss>=9.0.0

# Input (Windows)
pydirectinput>=1.0.4
pyclick>=1.0.0

# Input (Cross-platform fallback)
pyautogui>=0.9.54
keyboard>=0.13.5
pynput>=1.7.6

# Window detection
pygetwindow>=0.0.9

# Notifications
requests>=2.28.0

# Windows-only (optional, for best performance)
# dxcam>=0.0.5
# pywin32>=306
```

---

## Implementation Phases

### Phase 1: Modern UI
- Replace tkinter with customtkinter
- Implement new layout with detection status, stats, log
- Dark theme styling

### Phase 2: Screen Capture + Detection
- Add vision.py with MSS capture
- Implement multi-scale template matching
- Add fallback detection chain

### Phase 3: State Machine
- Implement state_machine.py
- Add state transitions and timeouts
- Connect detection to state changes

### Phase 4: Input Improvements
- Add input_handler.py with Bezier curves
- Implement Gaussian timing
- Add micro-jitter to clicks

### Phase 5: Setup Wizard
- Create setup_wizard.py
- Template capture UI with F8 hotkey
- Resolution-aware template storage

### Phase 6: Notifications
- Add Discord webhook support
- Improve sound notifications
- Add success/failure events

---

## Open Questions (Resolved)

1. ~~Does ARK:SA support Steam Source Query?~~ → Not critical, visual detection is sufficient
2. ~~DXcam vs MSS for Mac?~~ → Use MSS on Mac, DXcam Windows-only
3. ~~What about overlays?~~ → HSV filtering handles Discord/Steam overlays

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ARK UI changes | Template recapture via wizard |
| Anti-cheat detection | Human-like input patterns, no memory reading |
| Different resolutions | Multi-scale matching + per-resolution templates |
| Game in fullscreen | DXcam handles DirectX fullscreen |
| Overlays blocking | HSV color filtering ignores overlay colors |

---

## Success Metrics

- **Detection accuracy:** >95% for all UI states
- **False positive rate:** <5%
- **Retry success:** Bot recovers from failures without user intervention
- **User setup time:** <2 minutes for first-time template capture
