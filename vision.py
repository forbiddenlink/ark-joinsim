"""
Screen Capture and Template Matching Module for Ark JoinSim v4.

Provides:
- Cross-platform screen capture (MSS primary, DXcam optional on Windows)
- Multi-scale template matching with edge detection
- Fallback detection chain: exact match -> multi-scale -> HSV color -> ORB features
- ROI (region of interest) support for faster scanning
- Window detection for ARK: Survival Ascended

Usage:
    from vision import ScreenCapture, TemplateDetector, WindowFinder

    capture = ScreenCapture()
    detector = TemplateDetector(capture)
    window = WindowFinder()

    # Find ARK window
    region = window.get_window_region()

    # Find a template
    pos = detector.find_template("join_button", threshold=0.8)
    if pos:
        print(f"Found at {pos}")

    # Check if something is visible
    if detector.can_see("server_full"):
        print("Server is full!")
"""

import platform
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import logging

import numpy as np

# Platform detection
IS_WINDOWS = sys.platform == 'win32' or platform.system() == 'Windows'
IS_MACOS = sys.platform == 'darwin' or platform.system() == 'Darwin'
IS_LINUX = sys.platform.startswith('linux') or platform.system() == 'Linux'

try:
    import cv2
except ImportError:
    raise ImportError("OpenCV is required. Run: pip install opencv-python")

try:
    import mss
except ImportError:
    raise ImportError("MSS is required. Run: pip install mss")

# Optional DXcam for Windows (best performance)
HAS_DXCAM = False
if IS_WINDOWS:
    try:
        import dxcam
        HAS_DXCAM = True
    except ImportError:
        pass

# Optional pygetwindow for cross-platform window detection
try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

# Optional win32gui for Windows window detection (more reliable)
HAS_WIN32GUI = False
if IS_WINDOWS:
    try:
        import win32gui
        import win32con
        HAS_WIN32GUI = True
    except ImportError:
        pass


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Constants
ARK_WINDOW_TITLE = "ARK: Survival Ascended"
TEMPLATES_DIR = Path(__file__).parent / "templates"
MANIFEST_FILE = TEMPLATES_DIR / "manifest.json"


class WindowFinder:
    """Finds the ARK: Survival Ascended game window.

    Uses win32gui on Windows for better reliability, falls back to
    pygetwindow for cross-platform support.

    Attributes:
        window_title: The title to search for (default: ARK: Survival Ascended).
    """

    def __init__(self, window_title: str = ARK_WINDOW_TITLE):
        """Initialize the WindowFinder.

        Args:
            window_title: Window title to search for.
        """
        self.window_title = window_title
        self._cached_region: Optional[Tuple[int, int, int, int]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 1.0  # Cache window position for 1 second

    def find_window(self) -> Optional[Any]:
        """Find the ARK window handle.

        Returns:
            Window handle/object if found, None otherwise.
        """
        if HAS_WIN32GUI:
            return self._find_window_win32()
        elif HAS_PYGETWINDOW:
            return self._find_window_pygetwindow()
        else:
            logger.warning("No window detection library available")
            return None

    def _find_window_win32(self) -> Optional[int]:
        """Find window using win32gui (Windows only).

        Returns:
            Window handle (HWND) if found, None otherwise.
        """
        windows: List[int] = []

        def enum_callback(hwnd: int, results: List[int]) -> bool:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title in title:
                    results.append(hwnd)
            return True

        win32gui.EnumWindows(enum_callback, windows)
        return windows[0] if windows else None

    def _find_window_pygetwindow(self) -> Optional[Any]:
        """Find window using pygetwindow (cross-platform).

        Returns:
            Window object if found, None otherwise.
        """
        # getWindowsWithTitle is Windows-only in pygetwindow
        # On macOS, use getAllTitles and getWindowGeometry
        if hasattr(gw, 'getWindowsWithTitle'):
            windows = gw.getWindowsWithTitle(self.window_title)
            return windows[0] if windows else None
        
        # macOS fallback: search through all window titles
        if hasattr(gw, 'getAllTitles'):
            try:
                titles = gw.getAllTitles()
                for title in titles:
                    if self.window_title in title:
                        # On macOS, return the title as a pseudo-window object
                        # We'll handle geometry lookup separately
                        return {"title": title, "platform": "macos"}
            except Exception as e:
                logger.debug(f"Failed to enumerate windows: {e}")
        
        return None

    def get_window_region(self, use_cache: bool = True) -> Optional[Tuple[int, int, int, int]]:
        """Get the region (bounding box) of the ARK window.

        Args:
            use_cache: Whether to use cached region if still valid.

        Returns:
            Tuple of (left, top, right, bottom) or None if not found.
        """
        # Check cache
        if use_cache and self._cached_region is not None:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._cached_region

        window = self.find_window()
        if window is None:
            logger.debug("ARK window not found")
            return None

        region: Optional[Tuple[int, int, int, int]] = None

        if HAS_WIN32GUI and isinstance(window, int):
            # win32gui returns HWND
            try:
                rect = win32gui.GetWindowRect(window)
                region = (rect[0], rect[1], rect[2], rect[3])
            except Exception as e:
                logger.error(f"Failed to get window rect: {e}")
                return None
        elif HAS_PYGETWINDOW:
            # pygetwindow window object or macOS dict
            try:
                if isinstance(window, dict) and window.get("platform") == "macos":
                    # macOS: try to get window geometry by title
                    if hasattr(gw, 'getWindowGeometry'):
                        geom = gw.getWindowGeometry(window["title"])
                        if geom:
                            left, top, width, height = geom
                            region = (left, top, left + width, top + height)
                    else:
                        # Fall back to capturing full screen on macOS
                        logger.info("macOS window geometry not available, using full screen capture")
                        return None
                else:
                    region = (window.left, window.top, window.right, window.bottom)
            except Exception as e:
                logger.error(f"Failed to get window rect: {e}")
                return None

        if region:
            # Validate region has positive dimensions
            left, top, right, bottom = region
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                logger.warning(f"Invalid window dimensions: {width}x{height} (window may be minimized)")
                return None

            self._cached_region = region
            self._cache_time = time.time()
            logger.debug(f"ARK window region: {region}")

        return region

    def is_window_visible(self) -> bool:
        """Check if the ARK window is currently visible.

        Returns:
            True if window is visible, False otherwise.
        """
        window = self.find_window()
        if window is None:
            return False

        if HAS_WIN32GUI and isinstance(window, int):
            return win32gui.IsWindowVisible(window)
        elif HAS_PYGETWINDOW:
            try:
                return window.visible
            except AttributeError:
                # Some platforms may not have visible attribute
                try:
                    return window.isActive
                except AttributeError:
                    return True  # Assume visible if we can't check
        return False

    def bring_to_front(self) -> bool:
        """Bring the ARK window to the front.

        Returns:
            True if successful, False otherwise.
        """
        window = self.find_window()
        if window is None:
            return False

        try:
            if HAS_WIN32GUI and isinstance(window, int):
                win32gui.SetForegroundWindow(window)
                return True
            elif HAS_PYGETWINDOW:
                window.activate()
                return True
        except Exception as e:
            logger.error(f"Failed to bring window to front: {e}")

        return False


class ScreenCapture:
    """Handles screen capture using MSS (cross-platform) or DXcam (Windows).

    DXcam provides better performance on Windows (240+ FPS) but requires
    DirectX. MSS is the fallback for all platforms (30-60 FPS).

    Attributes:
        use_dxcam: Whether to use DXcam when available.
    """

    def __init__(self, use_dxcam: bool = True):
        """Initialize the ScreenCapture.

        Args:
            use_dxcam: Whether to prefer DXcam on Windows (default: True).
        """
        self.use_dxcam = use_dxcam and HAS_DXCAM
        self._dxcam_camera: Optional[Any] = None
        self._mss_context: Optional[mss.mss] = None

        # Threading support
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_time: float = 0
        self._capture_thread: Optional[threading.Thread] = None
        self._running: bool = False

        # Initialize capture backend
        self._init_backend()

    def _init_backend(self) -> None:
        """Initialize the capture backend (DXcam or MSS)."""
        if self.use_dxcam:
            try:
                self._dxcam_camera = dxcam.create()
                logger.info("Using DXcam for screen capture")
            except Exception as e:
                logger.warning(f"DXcam initialization failed: {e}, falling back to MSS")
                self.use_dxcam = False

        if not self.use_dxcam:
            self._mss_context = mss.mss()
            logger.info("Using MSS for screen capture")

    def capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[np.ndarray]:
        """Capture a screenshot.

        Args:
            region: Optional (left, top, right, bottom) region to capture.
                    If None, captures the entire primary monitor.

        Returns:
            BGR numpy array of the screenshot, or None on failure.
        """
        try:
            if self.use_dxcam and self._dxcam_camera:
                return self._capture_dxcam(region)
            else:
                return self._capture_mss(region)
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None

    def _capture_dxcam(
        self,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[np.ndarray]:
        """Capture using DXcam (Windows only).

        Args:
            region: Optional (left, top, right, bottom) region.

        Returns:
            BGR numpy array or None.
        """
        if self._dxcam_camera is None:
            return None

        # DXcam uses (left, top, right, bottom) format
        frame = self._dxcam_camera.grab(region=region)
        if frame is None:
            return None

        # DXcam returns RGB, convert to BGR for OpenCV
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def _capture_mss(
        self,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[np.ndarray]:
        """Capture using MSS (cross-platform).

        Args:
            region: Optional (left, top, right, bottom) region.

        Returns:
            BGR numpy array or None.
        """
        if self._mss_context is None:
            self._mss_context = mss.mss()

        if region:
            # Convert (left, top, right, bottom) to MSS format
            monitor = {
                "left": region[0],
                "top": region[1],
                "width": region[2] - region[0],
                "height": region[3] - region[1],
            }
        else:
            # Primary monitor (index 1 is primary, index 0 is "all monitors combined")
            if len(self._mss_context.monitors) < 2:
                logger.error("No monitors detected by MSS")
                return None
            monitor = self._mss_context.monitors[1]

        screenshot = self._mss_context.grab(monitor)

        # Convert to numpy array (BGRA -> BGR)
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def start_threaded_capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        fps: int = 30
    ) -> None:
        """Start continuous capture in a background thread.

        Args:
            region: Optional region to capture.
            fps: Target frames per second.
        """
        if self._running:
            return

        self._running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            args=(region, fps),
            daemon=True
        )
        self._capture_thread.start()
        logger.info(f"Started threaded capture at {fps} FPS")

    def stop_threaded_capture(self) -> None:
        """Stop the background capture thread."""
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            if self._capture_thread.is_alive():
                logger.warning("Capture thread did not stop cleanly within timeout")
            self._capture_thread = None
        logger.info("Stopped threaded capture")

    def _capture_loop(
        self,
        region: Optional[Tuple[int, int, int, int]],
        fps: int
    ) -> None:
        """Background capture loop.

        Args:
            region: Region to capture.
            fps: Target frames per second.
        """
        interval = 1.0 / fps

        while self._running:
            start = time.time()

            frame = self.capture(region)
            if frame is not None:
                with self._lock:
                    self._latest_frame = frame
                    self._frame_time = time.time()

            # Sleep to maintain target FPS
            elapsed = time.time() - start
            if elapsed < interval:
                time.sleep(interval - elapsed)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest captured frame (thread-safe).

        Returns:
            The latest frame or None if no frame available.
        """
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_frame_age(self) -> float:
        """Get the age of the latest frame in seconds.

        Returns:
            Age in seconds, or float('inf') if no frame.
        """
        with self._lock:
            if self._frame_time == 0:
                return float('inf')
            return time.time() - self._frame_time

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_threaded_capture()

        if self._dxcam_camera:
            try:
                del self._dxcam_camera
            except Exception:
                pass
            self._dxcam_camera = None

        if self._mss_context:
            try:
                self._mss_context.close()
            except Exception:
                pass
            self._mss_context = None

    def __del__(self):
        """Destructor to clean up resources."""
        self.cleanup()


class TemplateDetector:
    """Multi-scale template matching with fallback detection chain.

    Detection methods (in order of preference):
    1. Exact template match (fastest)
    2. Multi-scale with edge detection (handles resolution)
    3. HSV color filtering (handles overlays)
    4. Feature matching with ORB (slowest, most robust)

    Attributes:
        capture: ScreenCapture instance for grabbing frames.
        templates_dir: Directory containing template images.
    """

    def __init__(
        self,
        capture: ScreenCapture,
        templates_dir: Path = TEMPLATES_DIR
    ):
        """Initialize the TemplateDetector.

        Args:
            capture: ScreenCapture instance.
            templates_dir: Path to templates directory.
        """
        self.capture = capture
        self.templates_dir = templates_dir

        # Cache loaded templates
        self._template_cache: Dict[str, np.ndarray] = {}
        self._edge_cache: Dict[str, np.ndarray] = {}

        # ORB detector for feature matching
        self._orb = cv2.ORB_create(nfeatures=500)
        self._bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def load_template(self, name: str) -> Optional[np.ndarray]:
        """Load a template image by name.

        Args:
            name: Template name (without extension).

        Returns:
            BGR numpy array of the template, or None if not found.
        """
        if name in self._template_cache:
            return self._template_cache[name]

        # Try to find template file
        for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            path = self.templates_dir / f"{name}{ext}"
            if path.exists():
                template = cv2.imread(str(path))
                if template is not None:
                    self._template_cache[name] = template
                    logger.debug(f"Loaded template: {name}")
                    return template

        # Also try with resolution suffix
        # e.g., join_button_1920x1080.png
        for file in self.templates_dir.glob(f"{name}_*.*"):
            template = cv2.imread(str(file))
            if template is not None:
                self._template_cache[name] = template
                logger.debug(f"Loaded template: {file.name}")
                return template

        logger.warning(f"Template not found: {name}")
        return None

    def get_template_edge(self, template: np.ndarray) -> np.ndarray:
        """Get Canny edge detection of a template.

        Args:
            template: Template image (BGR).

        Returns:
            Edge-detected image.
        """
        # Use hash as cache key
        key = hash(template.tobytes())
        if key in self._edge_cache:
            return self._edge_cache[key]

        gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 200)
        self._edge_cache[key] = edges
        return edges

    def find_template(
        self,
        name: str,
        threshold: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None,
        use_fallbacks: bool = True
    ) -> Optional[Tuple[int, int]]:
        """Find a template on screen.

        Uses the fallback detection chain if the primary method fails.

        Args:
            name: Template name.
            threshold: Match confidence threshold (0.0-1.0).
            region: Optional ROI region (left, top, right, bottom).
            use_fallbacks: Whether to use fallback detection methods.

        Returns:
            Center (x, y) coordinates of the match, or None if not found.
        """
        template = self.load_template(name)
        if template is None:
            return None

        # Capture screen
        if self.capture._running:
            frame = self.capture.get_latest_frame()
        else:
            frame = self.capture.capture(region)

        if frame is None:
            logger.error("Failed to capture screen")
            return None

        # If we captured full screen but have a region, crop it
        if region and not self.capture._running:
            # Already captured with region
            pass

        # Detection chain
        result = self._exact_match(frame, template, threshold)
        if result:
            return self._adjust_for_region(result, region)

        if use_fallbacks:
            # Try multi-scale
            result = self._multiscale_match(frame, template, threshold)
            if result:
                return self._adjust_for_region(result, region)

            # Try HSV color matching
            result = self._hsv_match(frame, template, threshold)
            if result:
                return self._adjust_for_region(result, region)

            # Try ORB feature matching
            result = self._orb_match(frame, template, threshold)
            if result:
                return self._adjust_for_region(result, region)

        return None

    def _adjust_for_region(
        self,
        pos: Tuple[int, int],
        region: Optional[Tuple[int, int, int, int]]
    ) -> Tuple[int, int]:
        """Adjust coordinates to account for ROI region offset.

        Args:
            pos: Position within the captured region.
            region: The captured region (left, top, right, bottom).

        Returns:
            Adjusted screen coordinates.
        """
        if region:
            return (pos[0] + region[0], pos[1] + region[1])
        return pos

    def _exact_match(
        self,
        frame: np.ndarray,
        template: np.ndarray,
        threshold: float
    ) -> Optional[Tuple[int, int]]:
        """Exact template matching (fastest).

        Args:
            frame: Screen capture.
            template: Template to find.
            threshold: Match threshold.

        Returns:
            Center position or None.
        """
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            logger.debug(f"Exact match found: {max_val:.3f} at {max_loc}")
            return (center_x, center_y)

        return None

    def _multiscale_match(
        self,
        frame: np.ndarray,
        template: np.ndarray,
        threshold: float
    ) -> Optional[Tuple[int, int]]:
        """Multi-scale template matching with edge detection.

        Args:
            frame: Screen capture.
            template: Template to find.
            threshold: Match threshold.

        Returns:
            Center position or None.
        """
        # Convert to grayscale and get edges
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_edges = cv2.Canny(frame_gray, 50, 200)
        template_edges = self.get_template_edge(template)

        th, tw = template_edges.shape[:2]

        best_match = None
        best_val = 0

        # Try different scales
        for scale in np.linspace(0.5, 1.5, 15):
            # Resize template
            new_w = int(tw * scale)
            new_h = int(th * scale)

            if new_w < 10 or new_h < 10:
                continue
            if new_w > frame.shape[1] or new_h > frame.shape[0]:
                continue

            resized = cv2.resize(template_edges, (new_w, new_h))

            result = cv2.matchTemplate(frame_edges, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_val:
                best_val = max_val
                best_match = (max_loc, new_w, new_h)

        if best_val >= threshold and best_match:
            loc, w, h = best_match
            center_x = loc[0] + w // 2
            center_y = loc[1] + h // 2
            logger.debug(f"Multi-scale match found: {best_val:.3f} at {loc}")
            return (center_x, center_y)

        return None

    def _hsv_match(
        self,
        frame: np.ndarray,
        template: np.ndarray,
        threshold: float
    ) -> Optional[Tuple[int, int]]:
        """HSV color-based matching (handles overlays).

        This method extracts the dominant colors from the template and
        looks for regions with similar color distribution.

        Args:
            frame: Screen capture.
            template: Template to find.
            threshold: Match threshold.

        Returns:
            Center position or None.
        """
        # Convert to HSV
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        template_hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)

        # Calculate histogram of template
        hist_template = cv2.calcHist(
            [template_hsv], [0, 1], None, [30, 32], [0, 180, 0, 256]
        )
        cv2.normalize(hist_template, hist_template, 0, 255, cv2.NORM_MINMAX)

        th, tw = template.shape[:2]

        # Slide window and compare histograms
        best_match = None
        best_similarity = 0
        step = max(th // 4, tw // 4, 10)

        for y in range(0, frame.shape[0] - th, step):
            for x in range(0, frame.shape[1] - tw, step):
                roi = frame_hsv[y:y+th, x:x+tw]

                hist_roi = cv2.calcHist(
                    [roi], [0, 1], None, [30, 32], [0, 180, 0, 256]
                )
                cv2.normalize(hist_roi, hist_roi, 0, 255, cv2.NORM_MINMAX)

                similarity = cv2.compareHist(
                    hist_template, hist_roi, cv2.HISTCMP_CORREL
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = (x, y)

        if best_similarity >= threshold and best_match:
            center_x = best_match[0] + tw // 2
            center_y = best_match[1] + th // 2
            logger.debug(f"HSV match found: {best_similarity:.3f} at {best_match}")
            return (center_x, center_y)

        return None

    def _orb_match(
        self,
        frame: np.ndarray,
        template: np.ndarray,
        threshold: float
    ) -> Optional[Tuple[int, int]]:
        """ORB feature matching (slowest, most robust).

        Args:
            frame: Screen capture.
            template: Template to find.
            threshold: Match threshold (for feature count ratio).

        Returns:
            Center position or None.
        """
        # Convert to grayscale
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Detect keypoints and descriptors
        kp1, des1 = self._orb.detectAndCompute(template_gray, None)
        kp2, des2 = self._orb.detectAndCompute(frame_gray, None)

        if des1 is None or des2 is None:
            return None

        if len(des1) < 2 or len(des2) < 2:
            return None

        # Match features
        try:
            matches = self._bf_matcher.match(des1, des2)
        except cv2.error:
            return None

        if not matches:
            return None

        # Sort by distance
        matches = sorted(matches, key=lambda x: x.distance)

        # Use top matches
        good_matches = matches[:max(len(matches) // 4, 10)]

        # Check if we have enough good matches
        match_ratio = len(good_matches) / len(kp1) if kp1 else 0
        if match_ratio < threshold * 0.5:  # Lower threshold for ORB
            return None

        # Calculate center from matched keypoints
        if good_matches:
            points = [kp2[m.trainIdx].pt for m in good_matches]
            center_x = int(np.mean([p[0] for p in points]))
            center_y = int(np.mean([p[1] for p in points]))
            logger.debug(f"ORB match found: {match_ratio:.3f} ratio, {len(good_matches)} matches")
            return (center_x, center_y)

        return None

    def can_see(
        self,
        name: str,
        threshold: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """Check if a template is visible on screen.

        Args:
            name: Template name.
            threshold: Match confidence threshold.
            region: Optional ROI region.

        Returns:
            True if template is visible, False otherwise.
        """
        return self.find_template(name, threshold, region) is not None

    def find_all_templates(
        self,
        name: str,
        threshold: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None,
        max_results: int = 10
    ) -> List[Tuple[int, int]]:
        """Find all instances of a template on screen.

        Args:
            name: Template name.
            threshold: Match confidence threshold.
            region: Optional ROI region.
            max_results: Maximum number of results to return.

        Returns:
            List of (x, y) center coordinates.
        """
        template = self.load_template(name)
        if template is None:
            return []

        if self.capture._running:
            frame = self.capture.get_latest_frame()
        else:
            frame = self.capture.capture(region)

        if frame is None:
            return []

        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        h, w = template.shape[:2]
        results = []

        for pt in zip(*locations[::-1]):
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2

            # Adjust for region
            if region:
                center_x += region[0]
                center_y += region[1]

            # Avoid duplicates (within 10 pixels)
            is_duplicate = False
            for existing in results:
                if abs(existing[0] - center_x) < 10 and abs(existing[1] - center_y) < 10:
                    is_duplicate = True
                    break

            if not is_duplicate:
                results.append((center_x, center_y))

            if len(results) >= max_results:
                break

        return results

    def save_template(
        self,
        name: str,
        image: np.ndarray,
        resolution: Optional[str] = None
    ) -> Path:
        """Save a template image.

        Args:
            name: Template name.
            image: BGR image to save.
            resolution: Optional resolution suffix (e.g., "1920x1080").

        Returns:
            Path to the saved template.
        """
        if resolution:
            filename = f"{name}_{resolution}.png"
        else:
            filename = f"{name}.png"

        path = self.templates_dir / filename
        cv2.imwrite(str(path), image)

        # Clear cache
        if name in self._template_cache:
            del self._template_cache[name]

        logger.info(f"Saved template: {path}")
        return path

    def capture_template(
        self,
        name: str,
        region: Tuple[int, int, int, int],
        resolution: Optional[str] = None
    ) -> Optional[Path]:
        """Capture a region of the screen and save as template.

        Args:
            name: Template name.
            region: Region to capture (left, top, right, bottom).
            resolution: Optional resolution suffix.

        Returns:
            Path to saved template or None on failure.
        """
        frame = self.capture.capture(region)
        if frame is None:
            logger.error("Failed to capture template region")
            return None

        return self.save_template(name, frame, resolution)

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()
        self._edge_cache.clear()
        logger.debug("Template cache cleared")


# Convenience functions for direct usage
_default_window_finder: Optional[WindowFinder] = None
_default_capture: Optional[ScreenCapture] = None
_default_detector: Optional[TemplateDetector] = None


def get_window_region() -> Optional[Tuple[int, int, int, int]]:
    """Get the ARK window region.

    Returns:
        (left, top, right, bottom) or None if not found.
    """
    global _default_window_finder
    if _default_window_finder is None:
        _default_window_finder = WindowFinder()
    return _default_window_finder.get_window_region()


def find_template(
    name: str,
    threshold: float = 0.8
) -> Optional[Tuple[int, int]]:
    """Find a template on screen.

    Args:
        name: Template name.
        threshold: Match confidence.

    Returns:
        (x, y) center or None.
    """
    global _default_capture, _default_detector
    if _default_capture is None:
        _default_capture = ScreenCapture()
    if _default_detector is None:
        _default_detector = TemplateDetector(_default_capture)
    return _default_detector.find_template(name, threshold)


def can_see(name: str, threshold: float = 0.8) -> bool:
    """Check if a template is visible.

    Args:
        name: Template name.
        threshold: Match confidence.

    Returns:
        True if visible.
    """
    return find_template(name, threshold) is not None


if __name__ == "__main__":
    # Demo/test code
    print("Vision module test")
    print("-" * 40)

    # Test window finder
    print("\nTesting WindowFinder...")
    finder = WindowFinder()
    region = finder.get_window_region()
    if region:
        print(f"  ARK window found: {region}")
        print(f"  Size: {region[2] - region[0]}x{region[3] - region[1]}")
    else:
        print("  ARK window not found")

    # Test screen capture
    print("\nTesting ScreenCapture...")
    capture = ScreenCapture(use_dxcam=True)
    print(f"  Using DXcam: {capture.use_dxcam}")

    frame = capture.capture()
    if frame is not None:
        print(f"  Captured frame: {frame.shape}")
    else:
        print("  Capture failed")

    # Test threaded capture
    print("\nTesting threaded capture...")
    capture.start_threaded_capture(fps=10)
    time.sleep(0.5)

    latest = capture.get_latest_frame()
    if latest is not None:
        print(f"  Latest frame: {latest.shape}, age: {capture.get_frame_age():.3f}s")
    else:
        print("  No frame available")

    capture.stop_threaded_capture()

    # Test template detector
    print("\nTesting TemplateDetector...")
    detector = TemplateDetector(capture)
    print(f"  Templates dir: {detector.templates_dir}")

    # Cleanup
    capture.cleanup()
    print("\nDone!")
