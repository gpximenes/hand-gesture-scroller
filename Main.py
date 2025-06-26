#!/usr/bin/env python3
"""
Hand Gesture Mouse & Scroll Control with MediaPipe and Tkinter GUI.

Structure:
  - HandLandmark: enum of MediaPipe hand indices.
  - GestureConfig: shared configuration for thresholds and modes.
  - HandDetector: wraps MediaPipe to extract hand landmarks per frame.
  - GestureProcessor: converts landmarks, detects scroll/click gestures.
  - VirtualMouseController: moves OS cursor and handles click events.
  - ScrollController: scrolls the OS viewport based on gestures.
  - HandGestureApp: coordinates the GUI, video capture, and controllers.

Requirements:
  - mediapipe
  - opencv-python
  - pyautogui
  - Pillow
"""
import logging
import math
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Tuple, Optional, Any

import numpy as np
import cv2
import mediapipe as mp
import pyautogui
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import ttk
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import drawing_styles as mp_drawing_styles


# -------- Enums --------
class HandLandmark(Enum):
    """Enum for MediaPipe hand landmark indices."""
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20

class ClickMode(Enum):
    """Enum for click gesture modes."""
    INDEX_MIDDLE = auto()
    THUMB_INDEX = auto()

# -------- Configuration --------
DEFAULT_CLICK_THRESHOLD = 25  # px distance
DEFAULT_SCROLL_SPEED = 100    # px per step
DEFAULT_SCROLL_DURATION = 0.5  # seconds
DEFAULT_SMOOTHING = 0.5        # smoothing factor
DEFAULT_MAX_HANDS = 1          # max hands to detect
DEFAULT_DET_CONFIDENCE = 0.7   # detection confidence
DEFAULT_TRACK_CONFIDENCE = 0.7  # tracking confidence

@dataclass
class GestureConfig:
    """Configuration for gesture thresholds and scroll speed."""
    click_threshold: int = DEFAULT_CLICK_THRESHOLD
    scroll_speed: int = DEFAULT_SCROLL_SPEED
    mode: ClickMode = ClickMode.THUMB_INDEX
    scroll_duration: float = DEFAULT_SCROLL_DURATION
    smoothing: float = DEFAULT_SMOOTHING
    max_hands: int = DEFAULT_MAX_HANDS
    det_confidence: float = DEFAULT_DET_CONFIDENCE
    track_confidence: float = DEFAULT_TRACK_CONFIDENCE

# -------- Hand Detection --------
class HandDetector:
    """Wrapper for MediaPipe hand detection."""
    def __init__(self, max_hands: int = 1, det_conf: float = 0.7, track_conf: float = 0.7):
        self._mp_hands = mp_hands
        self._detector = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=det_conf,
            min_tracking_confidence=track_conf,
        )
        self._drawer = mp_drawing
        self._closed = False

    def process(self, frame) -> Optional[Any]:
        if self._closed or self._detector is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._detector.process(rgb)
        hand_landmarks = getattr(results, "multi_hand_landmarks", None)
        if hand_landmarks:
            return hand_landmarks[0]
        return None

    def draw(self, frame, hand_landmarks) -> None:
        self._drawer.draw_landmarks(frame, hand_landmarks, list(self._mp_hands.HAND_CONNECTIONS))

    def close(self) -> None:
        if not self._closed and self._detector is not None:
            try:
                self._detector.close()
            except Exception:
                pass
            self._closed = True
            self._detector = None

# -------- Gesture Processing --------
PixelPoint = Tuple[int, int]  # (x_px, y_px)

class GestureProcessor:
    """Processes hand landmarks for gestures."""
    @staticmethod
    def to_pixel_points(hand_landmarks, frame) -> Dict[HandLandmark, PixelPoint]:
        h, w, _ = frame.shape
        return {
            HandLandmark(i): (int(lm.x * w), int(lm.y * h))
            for i, lm in enumerate(hand_landmarks.landmark)
        }

    @staticmethod
    def is_scroll(pts: Dict[HandLandmark, PixelPoint], config: GestureConfig) -> bool:
        if config.mode == ClickMode.INDEX_MIDDLE:
            id1, id2 = HandLandmark.INDEX_FINGER_TIP, HandLandmark.MIDDLE_FINGER_TIP
        else:
            id1, id2 = HandLandmark.THUMB_TIP, HandLandmark.INDEX_FINGER_PIP
        x1, y1 = pts[id1]
        x2, y2 = pts[id2]
        return math.hypot(x2 - x1, y2 - y1) < config.click_threshold

    @staticmethod
    def is_click(pts: Dict[HandLandmark, PixelPoint], config: GestureConfig) -> bool:
        x1, y1 = pts[HandLandmark.INDEX_FINGER_TIP]
        x2, y2 = pts[HandLandmark.THUMB_TIP]
        return math.hypot(x2 - x1, y2 - y1) < config.click_threshold
    

# -------- Controllers --------
class VirtualMouseController:
    """Controls the OS mouse cursor using gestures."""
    def __init__(self, smoothing: float = 0.5):
        self.screen_w, self.screen_h = pyautogui.size()
        self.smoothing = smoothing
        self.prev: Optional[PixelPoint] = None

    def move(self, landmark, smoothing: Optional[float] = None) -> None:
        x = int(landmark.x * self.screen_w)
        y = int(landmark.y * self.screen_h)
        factor = smoothing if smoothing is not None else self.smoothing
        if self.prev:
            x = int(self.prev[0] + factor * (x - self.prev[0]))
            y = int(self.prev[1] + factor * (y - self.prev[1]))
        pyautogui.moveTo(x, y)
        self.prev = (x, y)

    def click(self) -> None:
        pyautogui.click()

class ScrollController:
    """Controls OS scrolling using gestures."""
    def __init__(self, config: GestureConfig):
        self.config = config
        self.active = False

    def scroll(self, direction: int, duration: float = 0.5) -> None:
        def _run():
            self.active = True
            end = time.time() + duration
            while time.time() < end:
                pyautogui.scroll(direction * self.config.scroll_speed)
                time.sleep(0.05)
            self.active = False
        if not self.active:
            threading.Thread(target=_run, daemon=True).start()

# -------- Main Application --------
class HandGestureApp:
    """Main application class for hand gesture control."""
    def __init__(self, root: tk.Tk):
        self.config = GestureConfig()
        self.detector = HandDetector()
        self.processor = GestureProcessor()
        self.mouse = VirtualMouseController()
        self.scroller = ScrollController(self.config)

        self.clicking = False
        self.show_video = tk.BooleanVar(value=True)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Webcam not accessible")

        self.root = root
        self._build_gui()
        self._update_loop()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_gui(self) -> None:
        """Builds the Tkinter GUI with all configuration options."""
        self.root.title("Hand Gesture Mouse & Scroll")
        # Video panel
        self.video_lbl = ttk.Label(self.root)
        self.video_lbl.pack(fill=tk.BOTH, expand=True)
        # Controls
        ctrl = ttk.LabelFrame(self.root, text="Configuration", padding=8)
        ctrl.pack(fill=tk.X, padx=8, pady=4)
        # Threshold
        ttk.Label(ctrl, text="Click Threshold:").grid(row=0, column=0, sticky=tk.W)
        self.entry_thresh = ttk.Entry(ctrl, width=5)
        self.entry_thresh.insert(0, str(self.config.click_threshold))
        self.entry_thresh.grid(row=0, column=1)
        self.scale_thresh = ttk.Scale(ctrl, from_=5, to=100, command=self._set_thresh)
        self.scale_thresh.set(self.config.click_threshold)
        self.scale_thresh.grid(row=0, column=2, sticky=tk.EW)
        # Speed
        ttk.Label(ctrl, text="Scroll Speed:").grid(row=1, column=0, sticky=tk.W)
        self.entry_speed = ttk.Entry(ctrl, width=5)
        self.entry_speed.insert(0, str(self.config.scroll_speed))
        self.entry_speed.grid(row=1, column=1)
        self.scale_speed = ttk.Scale(ctrl, from_=10, to=500, command=self._set_speed)
        self.scale_speed.set(self.config.scroll_speed)
        self.scale_speed.grid(row=1, column=2, sticky=tk.EW)
        # Scroll Duration
        ttk.Label(ctrl, text="Scroll Duration (s):").grid(row=2, column=0, sticky=tk.W)
        self.entry_scroll_duration = ttk.Entry(ctrl, width=5)
        self.entry_scroll_duration.insert(0, "0.5")
        self.entry_scroll_duration.grid(row=2, column=1)
        self.scale_scroll_duration = ttk.Scale(ctrl, from_=0.1, to=2.0, orient=tk.HORIZONTAL, command=self._set_scroll_duration)
        self.scale_scroll_duration.set(0.5)
        self.scale_scroll_duration.grid(row=2, column=2, sticky=tk.EW)
        # Smoothing
        ttk.Label(ctrl, text="Mouse Smoothing:").grid(row=3, column=0, sticky=tk.W)
        self.entry_smoothing = ttk.Entry(ctrl, width=5)
        self.entry_smoothing.insert(0, "0.5")
        self.entry_smoothing.grid(row=3, column=1)
        self.scale_smoothing = ttk.Scale(ctrl, from_=0.0, to=1.0, command=self._set_smoothing)
        self.scale_smoothing.set(0.5)
        self.scale_smoothing.grid(row=3, column=2, sticky=tk.EW)
        # Max Hands
        ttk.Label(ctrl, text="Max Hands:").grid(row=4, column=0, sticky=tk.W)
        self.entry_max_hands = ttk.Entry(ctrl, width=5)
        self.entry_max_hands.insert(0, "1")
        self.entry_max_hands.grid(row=4, column=1)
        self.scale_max_hands = ttk.Scale(ctrl, from_=1, to=2, command=self._set_max_hands)
        self.scale_max_hands.set(1)
        self.scale_max_hands.grid(row=4, column=2, sticky=tk.EW)
        # Detection Confidence
        ttk.Label(ctrl, text="Detection Confidence:").grid(row=5, column=0, sticky=tk.W)
        self.entry_det_conf = ttk.Entry(ctrl, width=5)
        self.entry_det_conf.insert(0, "0.7")
        self.entry_det_conf.grid(row=5, column=1)
        self.scale_det_conf = ttk.Scale(ctrl, from_=0.1, to=1.0, command=self._set_det_conf)
        self.scale_det_conf.set(0.7)
        self.scale_det_conf.grid(row=5, column=2, sticky=tk.EW)
        # Tracking Confidence
        ttk.Label(ctrl, text="Tracking Confidence:").grid(row=6, column=0, sticky=tk.W)
        self.entry_track_conf = ttk.Entry(ctrl, width=5)
        self.entry_track_conf.insert(0, "0.7")
        self.entry_track_conf.grid(row=6, column=1)
        self.scale_track_conf = ttk.Scale(ctrl, from_=0.1, to=1.0, command=self._set_track_conf)
        self.scale_track_conf.set(0.7)
        self.scale_track_conf.grid(row=6, column=2, sticky=tk.EW)
        # Mode
        ttk.Label(ctrl, text="Click Mode:").grid(row=7, column=0, sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.config.mode.name)
        ttk.OptionMenu(ctrl, self.mode_var, self.config.mode.name,
                       *[m.name for m in ClickMode], command=lambda _: self._set_mode(self.mode_var.get())).grid(row=7, column=1, columnspan=2, sticky=tk.EW)
        # Show video
        ttk.Checkbutton(ctrl, text="Show Video", variable=self.show_video).grid(row=8, column=0, columnspan=3)
        ctrl.columnconfigure(2, weight=1)

    def _set_thresh(self, val: str) -> None:
        """Update click threshold from slider."""
        t = int(float(val))
        self.config.click_threshold = t
        self.entry_thresh.delete(0, tk.END)
        self.entry_thresh.insert(0, str(t))

    def _set_speed(self, val: str) -> None:
        """Update scroll speed from slider."""
        s = int(float(val))
        self.config.scroll_speed = s
        self.entry_speed.delete(0, tk.END)
        self.entry_speed.insert(0, str(s))

    def _set_scroll_duration(self, val: str) -> None:
        d = float(val)
        self.entry_scroll_duration.delete(0, tk.END)
        self.entry_scroll_duration.insert(0, str(round(d, 2)))
        self.scroller.config.scroll_duration = d

    def _set_smoothing(self, val: str) -> None:
        s = float(val)
        self.entry_smoothing.delete(0, tk.END)
        self.entry_smoothing.insert(0, str(round(s, 2)))
        self.mouse.smoothing = s

    def _set_max_hands(self, val: str) -> None:
        m = int(float(val))
        self.entry_max_hands.delete(0, tk.END)
        self.entry_max_hands.insert(0, str(m))
        # Defensive: check for required attributes
        if not hasattr(self, 'entry_det_conf') or not hasattr(self, 'entry_track_conf'):
            print("Error: Detection/Tracking confidence entries not initialized.")
            return
        # Re-initialize detector with new max_hands
        if self.detector:
            self.detector.close()
        self.detector = HandDetector(max_hands=m,
                                     det_conf=float(self.entry_det_conf.get()),
                                     track_conf=float(self.entry_track_conf.get()))

    def _set_det_conf(self, val: str) -> None:
        c = float(val)
        self.entry_det_conf.delete(0, tk.END)
        self.entry_det_conf.insert(0, str(round(c, 2)))
        if not hasattr(self, 'entry_max_hands') or not hasattr(self, 'entry_track_conf'):
            print("Error: Max hands/tracking confidence entries not initialized.")
            return
        # Re-initialize detector with new confidence
        if self.detector:
            self.detector.close()
        self.detector = HandDetector(max_hands=int(self.entry_max_hands.get()),
                                     det_conf=c,
                                     track_conf=float(self.entry_track_conf.get()))

    def _set_track_conf(self, val: str) -> None:
        c = float(val)
        self.entry_track_conf.delete(0, tk.END)
        self.entry_track_conf.insert(0, str(round(c, 2)))
        if not hasattr(self, 'entry_max_hands') or not hasattr(self, 'entry_det_conf'):
            print("Error: Max hands/detection confidence entries not initialized.")
            return
        # Re-initialize detector with new confidence
        if self.detector:
            self.detector.close()
        self.detector = HandDetector(max_hands=int(self.entry_max_hands.get()),
                                     det_conf=float(self.entry_det_conf.get()),
                                     track_conf=c)

    def _set_mode(self, mode_name: str) -> None:
        """Update click mode from dropdown."""
        self.config.mode = ClickMode[mode_name]

    def _update_loop(self) -> None:
        """Main update loop for video capture and gesture processing."""
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            hand = self.detector.process(frame)
            if hand and hasattr(hand, 'landmark'):
                pts = self.processor.to_pixel_points(hand, frame)
                self.detector.draw(frame, hand)  # Draw landmarks before display
                # Scroll or pointer
                if self.processor.is_scroll(pts, self.config):
                    direction = 1 if pts[HandLandmark.INDEX_FINGER_TIP][1] < pts[HandLandmark.INDEX_FINGER_MCP][1] else -1
                    self.scroller.scroll(direction)
                else:

                    if(not self.clicking):
                        # Move cursor
                        self.mouse.move(hand.landmark[HandLandmark.INDEX_FINGER_TIP.value])
                        
                    # Click
                    if self.processor.is_click(pts, self.config) and not self.clicking:
                        self.mouse.click()
                        self.clicking = True
                    elif not self.processor.is_click(pts, self.config):
                        self.clicking = False
            # Display
            if self.show_video.get():
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = ImageTk.PhotoImage(image=Image.fromarray(rgb_frame))
                setattr(self.video_lbl, 'imgtk', img)  # Prevent garbage collection (Tkinter idiom)
                self.video_lbl.config(image=img)
        self.root.after(33, self._update_loop)

    def _on_close(self) -> None:
        """Cleanup on application close."""
        self.cap.release()
        self.detector.close()
        self.root.destroy()


def main() -> None:
    """Entry point for the application."""
    logging.basicConfig(level=logging.INFO)
    root = tk.Tk()
    app = HandGestureApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
