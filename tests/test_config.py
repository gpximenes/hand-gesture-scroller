import json

import pytest

from hand_gesture_scroller.config import Config


def test_validated_config_roundtrip(tmp_path):
    config = Config(scroll_speed=7)
    path = tmp_path / "settings.json"
    config.save(path)
    assert Config.load(path) == config
    assert json.loads(path.read_text())["scroll_speed"] == 7


@pytest.mark.parametrize(
    "values",
    [
        {"scroll_speed": 0},
        {"scroll_speed": True},
        {"smoothing": float("nan")},
        {"pinch_on": 0.8, "pinch_off": 0.4},
        {"keyboard_action": "rm -rf /"},
        {"camera_index": -1},
        {"stability_seconds": -1},
        {"unknown": 1},
    ],
)
def test_reject_invalid_config(values):
    with pytest.raises(ValueError):
        Config.from_dict(values)


def test_reject_non_object(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[]")
    with pytest.raises(ValueError, match="object"):
        Config.load(path)
