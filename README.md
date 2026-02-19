# Ark JoinSim v4 — Smart Auto-Joiner for Ark: Survival Ascended

A smart auto-joiner that **detects join failures and automatically retries**. No more getting stuck on "Server Full" popups.

**Built for:** Windows (with Mac/Linux support)

## What's New in v4

- **Smart Detection** — Detects "Server Full" popup, loading screens, and when you get kicked back
- **Auto-Retry** — Automatically dismisses popups and retries joining
- **Auto-Find Window** — No more manual "Set Position" — finds ARK automatically
- **Works at Any Resolution** — Multi-scale template matching adapts to your screen
- **Modern Dark UI** — Clean interface with live detection status and activity log
- **Discord Notifications** — Get pinged when you successfully join
- **Better Anti-Detection** — Bezier curve mouse movement, Gaussian timing distribution

## Features

### Smart Join Detection
- **Detects "Server Full" popup** and dismisses it automatically
- **Detects loading screen** to know join is in progress
- **Detects kick-back to server list** and retries
- **Detects successful join** and stops (spawn screen / HUD)
- **15-second timeout** for stuck joins

### Modern UI
- **Live detection status** — See what the bot can see
- **Activity log** — Scrolling history of all actions
- **Session stats** — Retry count, time elapsed, clicks
- **Settings panel** — Configure timeout, sounds, Discord webhook

### Anti-Detection (Improved)
- **Bezier curve mouse movement** — Natural curved paths, not linear
- **Gaussian timing distribution** — More human-like than uniform random
- **Micro-jitter during click hold** — Humans don't hold perfectly still
- **Position jitter** — Clicks slightly different spot each time (±5px)
- **Realistic click duration** — 50-150ms hold time

### Quality of Life
- **Discord notifications** — Get pinged on success/failure
- **Sound notifications** — Different sounds for different events
- **Auto-saves settings** — Remembers your preferences
- **Hotkey controls** — F6 to toggle, F7 to quit

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**On Windows (recommended):** Also install optional packages for better performance:
```bash
pip install pydirectinput dxcam pywin32
```

### 2. Verify Installation (Windows)

Run the diagnostics to make sure everything works:

```bash
# Quick check
test_windows.bat

# Full functionality test
python test_windows_full.py
```

This will verify:
- All dependencies installed
- Screen capture working
- Window detection working
- Input simulation working
- Vision module working

**If tests fail:**
1. Run Command Prompt as Administrator
2. Re-run `pip install -r requirements-windows.txt`
3. Check antivirus isn't blocking Python

### 3. First-Time Setup

Run the app — it will launch a setup wizard to capture template images:

```bash
python joinsim.py
```

The wizard will guide you to:
1. Capture the **Join button**
2. Capture the **"Server Full" popup**
3. Capture the **server list** background
4. (Optional) Capture the **loading screen**

This only needs to be done once per resolution.

### 4. Use It

1. **Launch Ark Ascended** and navigate to the server list
2. **Find your full server**
3. **Run JoinSim** and click **Start** (or press F6)
4. **Wait** — JoinSim will detect failures and keep retrying
5. **Get notified** when you successfully join!

## Configuration

Settings are saved to `joinsim_config.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `timeout_seconds` | 15 | How long to wait before assuming join failed |
| `detection_threshold` | 0.8 | Template matching confidence (0.0-1.0) |
| `sound_enabled` | true | Play sounds on events |
| `discord_webhook` | null | Discord webhook URL for notifications |

## File Structure

```
ark-joinsim/
├── joinsim.py          # Main application
├── vision.py           # Screen capture + template matching
├── input_handler.py    # Human-like mouse/keyboard
├── state_machine.py    # Join state tracking
├── notifications.py    # Discord + sounds
├── setup_wizard.py     # First-time template capture
├── templates/          # Your captured template images
├── requirements.txt
└── joinsim_config.json # Your settings
```

## How It Works

### State Machine

```
IDLE → SEARCHING → CLICKING → WAITING → SUCCESS!
                      ↓           ↓
                   RETRY ← FAILED (server full / timeout)
```

1. **SEARCHING** — Looking for ARK window and Join button
2. **CLICKING** — Found target, performing human-like click
3. **WAITING** — Clicked, monitoring for result (max 15 seconds)
4. **FAILED** — Detected popup or timeout, dismisses and retries
5. **SUCCESS** — Detected loading/spawn screen, stops bot

### Detection Methods

Uses OpenCV template matching with multiple fallback strategies:
1. **Exact match** — Fastest, works when resolution matches
2. **Multi-scale match** — Handles different resolutions
3. **HSV color match** — Ignores Discord/Steam overlays
4. **Feature matching** — Most robust for partial visibility

## Troubleshooting

**"Templates not found" on startup:**
- Run the setup wizard again: `python setup_wizard.py`
- Make sure ARK is visible when capturing

**Detection not working:**
- Lower the `detection_threshold` in settings (try 0.7)
- Recapture templates with overlays disabled
- Make sure ARK window is not minimized

**Bot keeps clicking but nothing happens:**
- Check that templates match your current ARK UI
- Try recapturing templates

**Discord notifications not working:**
- Verify webhook URL is correct (Settings → Discord Webhook)
- Check that the webhook has permission to post

## Requirements

- Python 3.8+
- Windows 10/11 (recommended) or Mac/Linux
- ~100MB disk space for dependencies

### Core Dependencies
- customtkinter (modern UI)
- opencv-python (template matching)
- mss (screen capture)
- pyautogui (input simulation)

### Optional (Windows)
- pydirectinput (better DirectX input)
- dxcam (faster screen capture, 240+ FPS)
- pywin32 (better window detection)

## Disclaimer

This tool is designed for quality-of-life on unofficial/private servers. Use at your own risk on official servers. The authors are not responsible for any bans or penalties.
