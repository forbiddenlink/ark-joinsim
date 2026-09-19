# Ark JoinSim v4

Windows desktop automation tool (Python, no web framework) that auto-joins full servers in
Ark: Survival Ascended. Uses OpenCV template matching on screen captures to detect "Server
Full" popups, loading screens, and successful joins, then retries with human-like mouse
movement. Cross-platform code paths exist but Windows is the primary target.

## Stack

- Python 3.8+, no package manager lockfile (plain `requirements.txt`)
- `customtkinter` - UI, `opencv-python` + `numpy` + `mss`/`Pillow` - vision/screen capture,
  `pyautogui` + `keyboard` + `pynput` - input simulation, `pygetwindow` - window detection,
  `requests` - Discord webhook notifications
- Windows-only extras in `requirements-windows.txt`: `pydirectinput`, `pywin32`, `bettercam`
  (preferred over `dxcam` for Windows 11)
- Packaged to a standalone `.exe` via PyInstaller (`joinsim.spec`, `build_exe.bat`)

## Commands

- `pip install -r requirements.txt` (or `requirements-windows.txt` on Windows, which adds
  `pydirectinput`, `pywin32`, `bettercam`)
- `python joinsim.py` - run the app (`run.bat` on Windows)
- `python setup_wizard.py` - first-time template capture wizard (also auto-launches from
  `joinsim.py` if templates are missing)
- `test.bat` / `python test_imports.py` - quick dependency check
- `python test_windows_full.py` - full Windows diagnostics (screen capture, window
  detection, input, vision)
- `build_exe.bat` - PyInstaller build using `joinsim.spec`, outputs a dist folder containing
  `JoinSim.exe`

## Layout

- `joinsim.py` - main application and UI
- `vision.py` - screen capture and template matching (exact, multi-scale, HSV color,
  feature-based fallbacks)
- `input_handler.py` - human-like mouse/keyboard input (Bezier curve movement, Gaussian
  timing, position jitter)
- `state_machine.py` - join state tracking (`IDLE -> SEARCHING -> CLICKING -> WAITING ->
  SUCCESS`, with `RETRY`/`FAILED` branches)
- `notifications.py` - Discord webhook + sound notifications
- `setup_wizard.py` - captures template images (Join button, "Server Full" popup, server
  list background, loading screen) once per resolution
- `templates/` - captured template images (user-generated, not committed content)
- `test_components.py`, `test_imports.py`, `test_windows_full.py` - test/diagnostic scripts
  run directly with `python`, not a pytest suite

## Configuration

Runtime settings persist to `joinsim_config.json` (not committed), not environment
variables: `timeout_seconds` (default 15), `detection_threshold` (default 0.8),
`sound_enabled`, `discord_webhook_url`.

## Conventions

- Hotkeys: F6 toggles the bot, F7 quits.
- Detection threshold and templates are resolution-specific; recapture templates after a
  resolution change or when overlays (Discord/Steam) interfere.
- `test_windows_full.py` checks `CI` env var to skip interactive prompts in automated runs.

## Gotchas

- No automated test runner config (no pytest.ini/pyproject.toml) - the `test_*.py` files are
  standalone scripts invoked directly.
- `requirements.txt` and `requirements-windows.txt` are separate, hand-maintained files that
  can drift; Windows-only packages are commented out in `requirements.txt` but uncommented
  in `requirements-windows.txt`.
