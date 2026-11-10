"""Single synchronous safety gate between intentions and desktop input."""

import importlib
import math


class Dispatcher:
    def __init__(self, backend_factory=None, keyboard_action=None):
        self.paused = True
        self.dry_run = True
        self.last_action = None
        self.error = None
        self._backend = None
        self._factory = backend_factory or (lambda: importlib.import_module("pyautogui"))
        self._keyboard_action = keyboard_action

    def pause(self):
        self.paused = True

    def resume(self):
        self.error = None
        self.paused = False

    def enable_input(self):
        """Explicit consent only; remain paused until a separate resume."""
        self.pause()
        try:
            backend = self._factory()
            if not backend.FAILSAFE:
                raise ValueError("PyAutoGUI fail-safe must remain enabled")
            self._backend = backend
            self.dry_run = False
            self.error = None
            return True
        except Exception as exc:
            self.dry_run = True
            self.error = str(exc)
            return False

    def disable_input(self):
        self.pause()
        self.dry_run = True
        self._backend = None

    def _validate(self, action):
        if action.kind == "move":
            if (
                not isinstance(action.value, (tuple, list))
                or len(action.value) != 2
                or any(
                    isinstance(v, bool)
                    or not isinstance(v, (float, int))
                    or not math.isfinite(v)
                    or not 0 <= v <= 1
                    for v in action.value
                )
            ):
                raise ValueError("move requires two finite normalized coordinates")
        elif action.kind == "scroll":
            if type(action.value) is not int or not 1 <= abs(action.value) <= 30:
                raise ValueError("scroll requires 1–30 signed wheel ticks")
        elif action.kind == "key":
            if action.value != "playpause" or self._keyboard_action != "playpause":
                raise ValueError("keyboard action not allowlisted")
        elif action.kind != "click" or action.value is not None:
            raise ValueError("action not allowlisted")

    def dispatch(self, action):
        if self.paused:
            return False
        try:
            self._validate(action)
            if not self.dry_run:
                backend = self._backend
                if not backend.FAILSAFE:
                    raise ValueError("PyAutoGUI fail-safe must remain enabled")
                if action.kind == "move":
                    width, height = backend.size()
                    x, y = action.value
                    # Never drive directly into PyAutoGUI's emergency corners.
                    backend.moveTo(
                        max(1, min(width - 2, round(x * (width - 1)))),
                        max(1, min(height - 2, round(y * (height - 1)))),
                    )
                elif action.kind == "scroll":
                    backend.scroll(action.value)
                elif action.kind == "click":
                    backend.click()
                else:
                    backend.press(action.value)
            self.last_action = action
            return True
        except Exception as exc:
            self.error = str(exc)
            self.pause()
            return False
