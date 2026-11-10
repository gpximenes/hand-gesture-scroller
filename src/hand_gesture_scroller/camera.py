"""MediaPipe Tasks VIDEO adapter, with explicit local model ownership."""

import importlib
import math
from pathlib import Path


class TasksDetector:
    def __init__(self, model_path, *, mp=None, cv=None):
        if not Path(model_path).is_file():
            raise ValueError("model file does not exist; supply hand_landmarker.task")
        self.mp = mp or importlib.import_module("mediapipe")
        self.cv = cv or importlib.import_module("cv2")
        vision = self.mp.tasks.vision
        options = vision.HandLandmarkerOptions(
            base_options=self.mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._detector = vision.HandLandmarker.create_from_options(options)
        self._timestamp = -1

    def detect(self, frame, now):
        if not math.isfinite(now) or now < 0:
            raise ValueError("camera timestamp must be finite and nonnegative")
        # VIDEO mode is synchronous, avoiding stale asynchronous action callbacks.
        timestamp = max(self._timestamp + 1, int(now * 1000))
        self._timestamp = timestamp
        rgb = self.cv.cvtColor(frame, self.cv.COLOR_BGR2RGB)
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self._detector.detect_for_video(image, timestamp)
        if not result.hand_landmarks:
            return None
        return [(point.x, point.y, point.z) for point in result.hand_landmarks[0]]

    def close(self):
        if self._detector is not None:
            self._detector.close()
            self._detector = None
