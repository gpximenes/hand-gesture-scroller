#!/usr/bin/env python3
"""
Hand Gesture Scrolling with MediaPipe and Tkinter GUI.

Captures webcam frames, detects hand landmarks,
recognizes a continuous scroll gesture (index and middle fingertips held together),
and scrolls the mouse up or down based on finger movement.

A Tkinter interface allows real-time tuning of:
  - click threshold
  - scroll speed
  - gesture mode
  - enable/disable scrolling
  - direct parameter entry
  - toggling video display

Requirements:
  - mediapipe
  - opencv-python
  - pyautogui
  - Pillow (for Tkinter image support)
"""
import logging
import math
import tkinter as tk
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import mediapipe as mp
import pyautogui
from PIL import Image, ImageTk
from tkinter import ttk

# Type alias for a landmark: (id, x_px, y_px)
Landmark = Tuple[int, int, int]

# Default configuration values (scroll_speed increased 10×)
DEFAULT_CLICK_THRESHOLD = 25      # pixels
DEFAULT_SCROLL_SPEED = 100        # pixels per scroll step


class ClickMode(Enum):
    """Gesture modes for scrolling."""
    INDEX_MIDDLE = auto()  # index & middle fingertips held
    THUMB_INDEX = auto()   # thumb tip & index PIP joint held


@dataclass
class GestureConfig:
    click_threshold: int = DEFAULT_CLICK_THRESHOLD
    scroll_speed: int = DEFAULT_SCROLL_SPEED
    mode: ClickMode = ClickMode.INDEX_MIDDLE


class HandGestureScrollerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Hand Gesture Scroller")
        self.config = GestureConfig()
        self.scrolling_enabled = True
        self.show_video = tk.BooleanVar(value=True)

        # MediaPipe hands setup
        self.mp_hands = mp.solutions.hands
        self.hand_detector = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.drawer = mp.solutions.drawing_utils

        # Video capture
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Webcam not accessible")

        self._build_gui()
        self._update_frame()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_gui(self) -> None:
        # Video panel
        self.video_lbl = ttk.Label(self.root)
        self.video_lbl.pack(fill=tk.BOTH, expand=True)

        # Control panel
        ctrl = ttk.Frame(self.root, padding=5)
        ctrl.pack(fill=tk.X)

        # On/Off scroll
        self.toggle_btn = ttk.Button(ctrl, text="Stop Scrolling", command=self._toggle_scrolling)
        self.toggle_btn.grid(row=0, column=0, padx=5)
        self.status_lbl = ttk.Label(ctrl, text="Scrolling: ON", foreground="green")
        self.status_lbl.grid(row=0, column=1, padx=5)

        # Show video checkbox
        self.video_cb = ttk.Checkbutton(ctrl, text="Show Video", variable=self.show_video, command=self._toggle_video)
        self.video_cb.grid(row=0, column=2, padx=5)

        # Click threshold label, scale, and entry
        ttk.Label(ctrl, text="Threshold (px):").grid(row=1, column=0, sticky=tk.W)
        self.thresh_scale = ttk.Scale(ctrl, from_=5, to=100, command=self._on_thresh_change)
        self.thresh_scale.set(self.config.click_threshold)
        self.thresh_scale.grid(row=1, column=1, sticky=tk.EW)
        self.thresh_entry = ttk.Entry(ctrl, width=5)
        self.thresh_entry.insert(0, str(self.config.click_threshold))
        self.thresh_entry.grid(row=1, column=2)
        self.thresh_entry.bind("<Return>", self._on_thresh_entry)

        # Scroll speed label, scale, and entry
        ttk.Label(ctrl, text="Speed (px/step):").grid(row=2, column=0, sticky=tk.W)
        self.speed_scale = ttk.Scale(ctrl, from_=10, to=500, command=self._on_speed_change)
        self.speed_scale.set(self.config.scroll_speed)
        self.speed_scale.grid(row=2, column=1, sticky=tk.EW)
        self.speed_entry = ttk.Entry(ctrl, width=5)
        self.speed_entry.insert(0, str(self.config.scroll_speed))
        self.speed_entry.grid(row=2, column=2)
        self.speed_entry.bind("<Return>", self._on_speed_entry)

        # Gesture mode dropdown
        ttk.Label(ctrl, text="Mode:").grid(row=3, column=0, sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.config.mode.name)
        mode_menu = ttk.OptionMenu(ctrl, self.mode_var, self.config.mode.name,
                                   *[mode.name for mode in ClickMode], command=self._on_mode_change)
        mode_menu.grid(row=3, column=1, columnspan=2, sticky=tk.EW)

        ctrl.columnconfigure(1, weight=1)

    def _toggle_scrolling(self) -> None:
        self.scrolling_enabled = not self.scrolling_enabled
        if self.scrolling_enabled:
            self.toggle_btn.config(text="Stop Scrolling")
            self.status_lbl.config(text="Scrolling: ON", foreground="green")
        else:
            self.toggle_btn.config(text="Start Scrolling")
            self.status_lbl.config(text="Scrolling: OFF", foreground="red")

    def _toggle_video(self) -> None:
        if self.show_video.get():
            self.video_lbl.pack(fill=tk.BOTH, expand=True)
        else:
            self.video_lbl.pack_forget()

    def _on_thresh_change(self, val: str) -> None:
        self.config.click_threshold = int(float(val))
        self.thresh_entry.delete(0, tk.END)
        self.thresh_entry.insert(0, str(self.config.click_threshold))

    def _on_speed_change(self, val: str) -> None:
        self.config.scroll_speed = int(float(val))
        self.speed_entry.delete(0, tk.END)
        self.speed_entry.insert(0, str(self.config.scroll_speed))

    def _on_thresh_entry(self, event) -> None:
        try:
            val = int(self.thresh_entry.get())
            self.config.click_threshold = val
            self.thresh_scale.set(val)
        except ValueError:
            pass

    def _on_speed_entry(self, event) -> None:
        try:
            val = int(self.speed_entry.get())
            self.config.scroll_speed = val
            self.speed_scale.set(val)
        except ValueError:
            pass

    def _on_mode_change(self, name: str) -> None:
        self.config.mode = ClickMode[name]

    def _update_frame(self) -> None:
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hand_detector.process(rgb)

            if results.multi_hand_landmarks and self.scrolling_enabled:
                lm = results.multi_hand_landmarks[0]
                pts = self._to_pixel_landmarks(lm, frame)
                self._draw_landmarks(frame, lm)
                if self._is_click(pts):
                    _, _, ty = pts[8]
                    _, _, by = pts[5]
                    direction = 1 if ty < by else -1
                    pyautogui.scroll(direction * self.config.scroll_speed)

            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            if self.show_video.get():
                self.video_lbl.imgtk = imgtk
                self.video_lbl.config(image=imgtk)

        self.root.after(33, self._update_frame)

    def _to_pixel_landmarks(self, hand_landmarks, frame) -> List[Landmark]:
        h, w, _ = frame.shape
        return [(i, int(lm.x*w), int(lm.y*h)) for i, lm in enumerate(hand_landmarks.landmark)]

    def _draw_landmarks(self, frame, hand_landmarks) -> None:
        self.drawer.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        h, w, _ = frame.shape
        for i in (8, 12, 5):
            lm = hand_landmarks.landmark[i]
            x, y = int(lm.x*w), int(lm.y*h)
            cv2.circle(frame, (x, y), 6, (0, 255, 0), cv2.FILLED)

    def _is_click(self, pts: List[Landmark]) -> bool:
        id1, id2 = (8, 12) if self.config.mode == ClickMode.INDEX_MIDDLE else (4, 6)
        _, x1, y1 = pts[id1]
        _, x2, y2 = pts[id2]
        return math.hypot(x2-x1, y2-y1) < self.config.click_threshold

    def _on_close(self) -> None:
        self.cap.release()
        self.hand_detector.close()
        self.root.destroy()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    root = tk.Tk()
    HandGestureScrollerApp(root)
    root.mainloop()
