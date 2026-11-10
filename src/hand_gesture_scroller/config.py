"""Strict, portable JSON settings. Safety arming is never persisted."""

import json
import math
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class Config:
    pinch_on: float = 0.25
    pinch_off: float = 0.4
    scroll_deadzone: float = 0.12
    scroll_speed: float = 8.0
    scroll_interval: float = 0.1
    stability_seconds: float = 0.12
    click_cooldown: float = 0.45
    smoothing: float = 0.35
    keyboard_action: str | None = None
    camera_index: int = 0
    model_path: str = ""

    def __post_init__(self):
        bounds = {
            "pinch_on": (0.01, 1.0),
            "pinch_off": (0.02, 1.5),
            "scroll_deadzone": (0.01, 1.0),
            "scroll_speed": (0.1, 30),
            "scroll_interval": (0.03, 2),
            "stability_seconds": (0, 2),
            "click_cooldown": (0.1, 5),
            "smoothing": (0.01, 1),
        }
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not low <= value <= high
            ):
                raise ValueError(f"{name} must be a finite number in [{low}, {high}]")
        if self.pinch_on >= self.pinch_off:
            raise ValueError("pinch_on must be smaller than pinch_off (release hysteresis)")
        if self.keyboard_action not in (None, "playpause"):
            raise ValueError("keyboard_action must be null or 'playpause'")
        if type(self.camera_index) is not int or self.camera_index < 0:
            raise ValueError("camera_index must be a nonnegative integer")
        if not isinstance(self.model_path, str):
            raise ValueError("model_path must be a string")

    @classmethod
    def from_dict(cls, values):
        if not isinstance(values, dict):
            raise ValueError("configuration must be a JSON object")
        unknown = values.keys() - {field.name for field in fields(cls)}
        if unknown:
            raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
        return cls(**values)

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
