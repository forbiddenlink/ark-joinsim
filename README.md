# Ark JoinSim v2 — Auto-Joiner for Ark: Survival Ascended

A smart auto-clicker / auto-joiner for getting into full Ark Ascended servers.

**Built for:** Windows laptop (optimized for different screen resolutions)

## Features

### Core
- **Auto-clicks Join button** until a server slot opens
- **Human-like clicking** — not detectable as a simple macro
- **Click position learning** — click once to set the Join button location
- **Hotkey controls** — F6 to toggle, F7 to quit
- **Simple GUI** — no command line needed

### Anti-Detection (v2)
- **Mouse down/up delay** — holds click for realistic duration (50-150ms)
- **Position jitter** — clicks slightly different spot each time (±5px)
- **Timing variance** — random delays between clicks
- **Random pauses** — occasionally waits 3-8 seconds (looks human)
- **Smooth mouse movement** — moves to position with slight curve

### Quality of Life
- **Click counter** — shows how many clicks this session
- **Auto-saves settings** — remembers position and preferences
- **Works on any resolution** — laptop or desktop

## Quick Start

### Option 1: Run from Python
```bash
# Install dependencies (one time)
pip install pyautogui keyboard pynput pillow

# Run
python joinsim.py
```

### Option 2: Use the batch files (Windows)
```
1. Double-click install.bat (one time)
2. Double-click run.bat
```

### Option 3: Build standalone exe
```bash
# Creates dist/JoinSim.exe
build_exe.bat
```

## How to Use

1. **Launch Ark Ascended** and navigate to the server list
2. **Find your full server** (shows 70/70 or whatever the max is)
3. **Run JoinSim**
4. **Click "Set Position"** → then click Ark's Join button
5. **Click "Start"** (or press F6)
6. **Wait** — JoinSim will keep clicking until you get in
7. **Press F6 to pause** or **F7 to quit**

## Configuration

Settings are saved to `joinsim_config.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `interval` | 2.5s | Base time between clicks |
| `jitter` | 0.8s | Random variance (±) added to interval |
| `position_jitter` | 5px | Random variance in click position |
| `click_duration_min` | 0.05s | Minimum mouse-down hold time |
| `click_duration_max` | 0.15s | Maximum mouse-down hold time |
| `random_pause_chance` | 10% | Chance of a longer random pause |
| `random_pause_min` | 3.0s | Minimum random pause |
| `random_pause_max` | 8.0s | Maximum random pause |

## Why This Works Better Than Simple Auto-Clickers

1. **Realistic click duration** — Most auto-clickers click instantly (0ms hold). Humans hold the mouse button for 50-150ms. Anti-cheat can detect instant releases.

2. **Position variance** — Humans don't click the exact same pixel every time. We add ±5px jitter.

3. **Timing variance** — Humans don't click at perfectly regular intervals. We add randomness.

4. **Random pauses** — Real humans occasionally pause to check their phone, take a sip, etc. We simulate this.

5. **Smooth mouse movement** — We move the cursor to the button with a slight curve, not teleport.

## Troubleshooting

**Click is in the wrong spot:**
- Re-run "Set Position"
- Make sure Ark is in the same windowed/fullscreen mode

**Not clicking:**
- Make sure Ark window is in focus
- Check that JoinSim shows "Running" status

**Still can't get in after 100+ clicks:**
- Server might be legitimately full with no one leaving
- Try a different time (early morning is usually less busy)

**Anti-cheat warning:**
- This tool is designed to look human-like, but use at your own risk on official servers
- Unofficial/private servers generally don't care about auto-clickers

## Laptop vs Desktop

JoinSim saves your screen resolution. If you switch between laptop and desktop:
- Just re-run "Set Position" on each device
- Settings are per-device based on resolution

## Requirements

- Windows 10/11
- Python 3.8+ (or use the standalone .exe)
- pyautogui, keyboard, pynput, Pillow
