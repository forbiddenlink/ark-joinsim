# Ark JoinSim — Auto-Joiner for Ark: Survival Ascended

A simple auto-clicker / auto-joiner for getting into full Ark Ascended servers.

**Built for:** Windows laptop (optimized for different screen resolutions)

## Features
- **Auto-detects screen resolution** — works on laptop or desktop without manual config
- **Click position learning** — click once to set the "Join" button location
- **Configurable click interval** — default 2 seconds, adjustable
- **Hotkey start/stop** — F6 to toggle, F7 to quit
- **Simple GUI** — no command line needed
- **Portable** — single exe, no install required

## Quick Start

### Option 1: Run from Python
```bash
# Install dependencies
pip install pyautogui keyboard pynput pillow

# Run
python joinsim.py
```

### Option 2: Use the exe (coming soon)
Download `JoinSim.exe` from releases and run it.

## How to Use

1. **Launch Ark Ascended** and navigate to the server list
2. **Run JoinSim**
3. **Click "Set Join Button Position"** then click the Join button in Ark
4. **Click "Start"** (or press F6)
5. JoinSim will click the join button every 2 seconds until you stop it
6. **Press F6 to pause** or **F7 to quit**

## Configuration

Settings are saved to `joinsim_config.json`:
- `click_x`, `click_y` — position of the Join button
- `interval` — seconds between clicks (default: 2.0)
- `resolution` — your screen resolution (auto-detected)

## Laptop vs Desktop

JoinSim auto-scales click positions based on resolution:
- If you set it up on a 1920x1080 desktop, it will adjust for a 1366x768 laptop
- Just re-run "Set Join Button Position" if the click is off

## Troubleshooting

**Click is in the wrong spot:**
- Re-run "Set Join Button Position"
- Make sure Ark is in the same windowed/fullscreen mode you'll use

**Not clicking:**
- Make sure Ark window is focused
- Check that JoinSim shows "Running" status

**Ark detects it as a bot:**
- Add randomness to click interval (built-in: ±0.5s jitter)
- Don't run it for hours straight
