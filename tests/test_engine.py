import pytest
from test_recognition import landmarks

from hand_gesture_scroller.config import Config
from hand_gesture_scroller.engine import Engine


def test_stability_then_pointer_and_immediate_fist_stop():
    engine = Engine()
    assert engine.update(landmarks((0,)), 0) == []
    (action,) = engine.update(landmarks((0,)), 0.13)
    assert action.kind == "move"
    assert 0 <= action.value[0] <= 1
    assert engine.update(landmarks(), 0.14) == []
    assert engine.gesture == "neutral"


def test_scroll_anchor_deadzone_rate_and_sign():
    engine = Engine(Config(stability_seconds=0))
    assert engine.update(landmarks((0, 1)), 0) == []
    assert engine.update(landmarks((0, 1), dy=0.01), 0.1) == []
    (down,) = engine.update(landmarks((0, 1), dy=0.15), 0.2)
    assert down.kind == "scroll" and down.value < 0
    assert engine.update(landmarks((0, 1), dy=0.15), 0.21) == []
    (up,) = engine.update(landmarks((0, 1), dy=-0.15), 0.31)
    assert up.value > 0
    assert engine.update(None, 0.4) == []
    assert engine.update(landmarks((0, 1), dy=0.2), 0.5) == []


def test_click_edge_hysteresis_cooldown():
    engine = Engine(Config(stability_seconds=0))
    closed = landmarks((0,), pinch=True)
    assert engine.update(closed, 0)[0].kind == "click"
    assert engine.update(closed, 1) == []
    halfway = list(closed)
    halfway[4] = (halfway[8][0] + 0.12, halfway[8][1], 0)
    assert engine.update(halfway, 1.1) == []
    assert engine.update(closed, 1.2) == []
    engine.update(landmarks((0,)), 1.3)
    assert engine.update(closed, 1.4)[0].kind == "click"
    engine.update(landmarks((0,)), 1.5)
    assert engine.update(closed, 1.6) == []
    assert engine.update(closed, 2) == []  # cooldown cannot queue a delayed click


def test_palm_is_opt_in_edge_triggered():
    points = landmarks((0, 1, 2, 3))
    assert Engine(Config(stability_seconds=0)).update(points, 0) == []
    engine = Engine(Config(stability_seconds=0, keyboard_action="playpause"))
    (action,) = engine.update(points, 0)
    assert (action.kind, action.value) == ("key", "playpause")
    assert engine.update(points, 1) == []


def test_invalid_time_and_hand_reset():
    engine = Engine(Config(stability_seconds=0))
    engine.update(landmarks((0,)), 1)
    with pytest.raises(ValueError, match="monotonic"):
        engine.update(None, 0)
    with pytest.raises(ValueError):
        engine.update(None, float("nan"))
    assert engine.update([(0, 0, 0)] * 21, 2) == []
    assert engine.gesture == "no hand"
