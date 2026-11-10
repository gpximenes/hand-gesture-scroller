"""Injected frame-to-action lifecycle, shared by UI and hardware-free integration tests."""


class Session:
    def __init__(self, capture, detector, engine, dispatcher, transform=None):
        self.capture = capture
        self.detector = detector
        self.engine = engine
        self.dispatcher = dispatcher
        self.transform = transform or (lambda frame: frame)
        self.error = None
        self.closed = False
        self.points = None

    def pause(self):
        self.dispatcher.pause()
        self.engine.reset()

    def toggle_pause(self):
        if self.closed:
            return
        if self.dispatcher.paused:
            self.engine.reset()
            self.dispatcher.resume()
        else:
            self.pause()

    def set_input(self, enabled):
        self.pause()
        if enabled:
            return self.dispatcher.enable_input()
        self.dispatcher.disable_input()
        return True

    def step(self, now):
        if self.closed:
            return None
        try:
            ok, frame = self.capture.read()
            if not ok or frame is None:
                raise RuntimeError(
                    "Camera read failed. Check Windows camera privacy and connection."
                )
            frame = self.transform(frame)
            self.points = self.detector.detect(frame, now)
            actions = self.engine.update(self.points, now)
            if self.dispatcher.paused:
                # Preview still recognizes poses, but no state may accumulate while paused.
                gesture = self.engine.gesture
                self.engine.reset()
                self.engine.gesture = gesture
            else:
                for action in actions:
                    if not self.dispatcher.dispatch(action):
                        self.engine.reset()
                        break
            return frame
        except Exception as exc:
            self.error = str(exc) or type(exc).__name__
            self.close()
            return None

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.pause()
        for cleanup in (self.capture.release, self.detector.close):
            try:
                cleanup()
            except Exception as exc:
                self.error = self.error or f"Cleanup failed: {exc}"
