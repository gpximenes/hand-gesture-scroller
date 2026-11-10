import math

import pytest

from hand_gesture_scroller.recognition import observe


def landmarks(extended=(), pinch=False, dy=0):
    """Synthetic palm; deliberately not a camera accuracy benchmark."""
    points = [(0.5, 0.85, 0.0)] * 21
    points[4] = (0.08, 0.62, 0)
    for finger, base in enumerate((5, 9, 13, 17)):
        x = 0.32 + finger * 0.12
        points[base] = (x, 0.65, 0)
        if finger in extended:
            points[base + 1] = (x, 0.45, 0)
            points[base + 2] = (x, 0.30, 0)
            points[base + 3] = (x, 0.15, 0)
        else:
            points[base + 1] = (x, 0.50, 0)
            points[base + 2] = (x, 0.61, 0)
            points[base + 3] = (x, 0.73, 0)
    if pinch:
        points[4] = (points[8][0] + 0.025, points[8][1], 0)
    return tuple((x, y + dy, z) for x, y, z in points)


@pytest.mark.parametrize(
    ("fingers", "gesture"),
    [
        ((), "neutral"),
        ((0,), "pointer"),
        ((0, 1), "scroll"),
        ((0, 1, 2, 3), "palm"),
        ((0, 2), "neutral"),
    ],
)
def test_orientation_and_scale_invariant(fingers, gesture):
    points = landmarks(fingers)
    for angle in (0, 0.7, math.pi, -math.pi / 2):
        rotated = tuple(
            (
                0.4 * (x * math.cos(angle) - y * math.sin(angle)) + 0.2,
                0.4 * (x * math.sin(angle) + y * math.cos(angle)) + 0.3,
                z,
            )
            for x, y, z in points
        )
        assert observe(rotated).gesture == gesture
        assert observe(tuple((-x, y, z) for x, y, z in rotated)).gesture == gesture


def test_pinch_distance_is_palm_relative():
    hand = observe(landmarks((0,), pinch=True))
    assert hand.gesture == "pinch"
    assert hand.pinch_ratio < 0.1


@pytest.mark.parametrize("points", [[], [(float("nan"), 0, 0)] * 21, [(0, 0, 0)] * 21])
def test_invalid_or_degenerate_hand_is_rejected(points):
    with pytest.raises(ValueError):
        observe(points)
