"""Deterministic temporal recognition. Produces intentions, never desktop input."""

import math
from dataclasses import dataclass

from .config import Config
from .recognition import observe


@dataclass(frozen=True)
class Action:
    kind: str
    value: object = None


class Engine:
    def __init__(self, config=None):
        self.config = config or Config()
        self._time = -math.inf
        self._last_click = -math.inf
        self.reset()

    def reset(self):
        """Discard tracking state at hand loss, pause, or mode change."""
        self.gesture = "no hand"
        self._candidate = None
        self._since = 0
        self._anchor = None
        self._pointer = None
        self._pinched = False
        self._palm = False
        self._last_scroll = -math.inf

    def update(self, points, now):
        if not math.isfinite(now) or now < self._time:
            raise ValueError("timestamps must be finite and monotonic")
        self._time = now
        try:
            hand = observe(points, self.config.pinch_on) if points is not None else None
        except (ValueError, TypeError):
            hand = None
        if hand is None:
            self.reset()
            return []
        gesture = hand.gesture
        if self._pinched and hand.pinch_ratio < self.config.pinch_off:
            gesture = "pinch"
        elif hand.pinch_ratio >= self.config.pinch_off:
            self._pinched = False
        if gesture != "palm":
            self._palm = False
        if gesture != self._candidate:
            self._candidate, self._since = gesture, now
            self._anchor = None
            self._pointer = None
        self.gesture = gesture
        if now - self._since < self.config.stability_seconds:
            return []
        if gesture == "pinch":
            if self._pinched:
                return []
            self._pinched = True
            if now - self._last_click >= self.config.click_cooldown:
                self._last_click = now
                return [Action("click")]
        elif gesture == "pointer":
            target = tuple(max(0.0, min(1.0, v)) for v in hand.pointer)
            if self._pointer is not None:
                target = tuple(
                    a + self.config.smoothing * (b - a)
                    for a, b in zip(self._pointer, target, strict=True)
                )
            self._pointer = target
            return [Action("move", target)]
        elif gesture == "scroll":
            if self._anchor is None:
                self._anchor = hand.center_y
                return []
            displacement = (self._anchor - hand.center_y) / hand.palm_scale
            if (
                abs(displacement) > self.config.scroll_deadzone
                and now - self._last_scroll >= self.config.scroll_interval
            ):
                self._last_scroll = now
                ticks = max(1, round(min(abs(displacement), 1) * self.config.scroll_speed))
                return [Action("scroll", ticks if displacement > 0 else -ticks)]
        elif gesture == "palm" and not self._palm:
            self._palm = True
            if self.config.keyboard_action:
                return [Action("key", self.config.keyboard_action)]
        return []
