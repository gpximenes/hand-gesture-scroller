# Hand Gesture Scroller

A versatile desktop tool that turns simple hand movements into smooth, continuous scrolling on your computer. By combining cutting-edge gesture detection (MediaPipe + OpenCV) with an intuitive Tkinter interface, anyone can browse, read, or work hands‑free.

---

## Features

* **Continuous scroll**: Hold index and middle fingers together (or thumb and index) to scroll up/down.
* **Configurable controls** via GUI:

  * Click distance threshold (px)
  * Scroll speed (px/step)
  * Gesture mode selection
  * Start/stop scrolling toggle
  * Enable/disable video preview
* **Live video feed** with optional overlay of hand landmarks.
* Smooth rendering at \~30 FPS.

## Dependencies

* Python 3.7+
* [mediapipe](https://github.com/google/mediapipe)
* [opencv-python](https://pypi.org/project/opencv-python/)
* [pyautogui](https://pypi.org/project/PyUserInput/)
* [Pillow](https://pypi.org/project/Pillow/) (for Tkinter image support)

Install via pip:

```bash
pip install mediapipe opencv-python pyautogui Pillow
```

## Usage

1. Clone this repository:

   ```bash
   git clone [https://github.com/yourusername/hand-gesture-scroller.git](https://github.com/gpximenes/hand-gesture-scroller.git)
   cd hand-gesture-scroller
   ```


2. Run the application:
   ```bash
    python hand_gesture_scroller.py
    ```

3. GUI Controls:

   * **Stop Scrolling** / **Start Scrolling**: Toggle gesture-based scrolling.
   * **Show Video**: Show or hide webcam feed.
   * **Threshold (px)**: Maximum distance between fingertips to count as "click" gesture.
   * **Speed (px/step)**: Amount to scroll per frame while gesture is held.
   * **Mode**: Choose between `INDEX_MIDDLE` or `THUMB_INDEX` gestures.



## Customization

* **Adjust defaults** in the `GestureConfig` dataclass at the top of `hand_gesture_scroller.py`.
* **Add new gestures** by extending the `ClickMode` enum and updating `_is_click()` logic.
* **Logging**: Configured via `logging.basicConfig()`; change level or format as needed.

## Troubleshooting

* **Webcam not accessible**: Ensure your camera is not used by another application.



