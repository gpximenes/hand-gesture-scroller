"""Palm-relative geometry; no image pixels or upright-hand assumptions."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    gesture: str
    pointer: tuple[float, float]
    center_y: float
    palm_scale: float
    pinch_ratio: float


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def extended(points, base):
    mcp, pip, dip, tip = points[base : base + 4]
    # A straight PIP joint AND a tip projecting away from the palm.
    a = tuple(x - y for x, y in zip(mcp, pip, strict=True))
    b = tuple(x - y for x, y in zip(tip, pip, strict=True))
    norm = distance(mcp, pip) * distance(tip, pip)
    if norm < 1e-9:
        return False
    cosine = sum(x * y for x, y in zip(a, b, strict=True)) / norm
    return cosine < -0.65 and distance(tip, mcp) > 1.35 * distance(pip, mcp)


def observe(points, pinch_on=0.25):
    if len(points) != 21 or any(
        len(p) != 3 or any(not math.isfinite(v) for v in p) for p in points
    ):
        raise ValueError("expected 21 finite xyz landmarks")
    scale = max(distance(points[5], points[17]), distance(points[0], points[9]))
    if scale < 1e-6:
        raise ValueError("degenerate palm")
    fingers = tuple(extended(points, base) for base in (5, 9, 13, 17))
    ratio = distance(points[4], points[8]) / scale
    gesture = "neutral"
    if ratio <= pinch_on:
        gesture = "pinch"
    elif fingers == (True, False, False, False):
        gesture = "pointer"
    elif fingers == (True, True, False, False):
        gesture = "scroll"
    elif all(fingers):
        gesture = "palm"
    return Observation(gesture, points[8][:2], points[9][1], scale, ratio)
