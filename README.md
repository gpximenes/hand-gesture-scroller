# Hand Gesture Scroller

Control your desktop hands-free with wearable-free webcam gestures. A held
pinch clicks, an open index finger drives the pointer, index+middle scrolls
up and down in the focused application, and a flat palm is an optional
media play/pause toggle.

Safety is the core design: the app **starts paused and dry-run**, and it
cannot inject a single mouse or keyboard event until you explicitly opt in
twice. Everything that matters is unit-tested headlessly; the deterministic
`demo` command runs without a camera, OpenCV, MediaPipe, or a display.

## Gestures

| Pose | Action | Notes |
| --- | --- | --- |
| Index finger only | Pointer movement | Smoothed; normalized to the primary monitor |
| Thumb + index together | Click | One click per pinch (release hysteresis + cooldown) |
| Index + middle, move hand | Scroll up / down | Dead zone + rate limit; evaluated per observation |
| Flat open palm | Play / pause (optional) | Allowlisted `mediapipe` key only; off by default |
| Closed fist or no hand | Nothing | Transient state resets on hand loss |

Hold index+middle, then move your whole hand up or down to scroll. Drop back
to a neutral fist to stop. Scroll is measured as wheel ticks against an
anchor you set by entering the pose, so it works at any camera distance or
preview resolution.

## Requirements

- **Python 3.10–3.12** (3.11 recommended)
- A webcam
- The [MediaPipe hand landmarker model](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task)
  (a local `.task` file; the app never downloads one itself)
- OS input works on **Windows and X11 Linux/macOS**. Wayland and full
  multi-monitor DPI behavior are not supported without per-device testing.

> **Target OS note:** This is a local desktop-control application, not a
> network service. The process owns the webcam and can only control input on
> the same computer running it. There is deliberately no LAN/web exposure.

## Install

```sh
git clone https://github.com/gpximenes/hand-gesture-scroller.git
cd hand-gesture-scroller
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Core + desktop camera/input stack:
pip install -e ".[desktop]"
```

Download the hand-landmarker model into the repository root (with the flag
guaranteeing a local file):

```sh
curl -L -o hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

## Usage

### 1. Headless demo (no hardware)

```sh
gesture-scroller demo
```

Runs the real gesture engine over synthetic landmarks and prints the
dispatched actions — a deterministic, dependency-free smoke test.

### 2. Safe preview (dry-run, no input)

```sh
gesture-scroller run --model hand_landmarker.task
```

Opens the preview window. **Nothing moves your mouse or scrolls.** You can
exercise every gesture visually and have the recognition layer classify
them; no OS input is possible. `<Escape>` pauses, the window's **Stop**
button stops, and closing releases the camera.

### 3. Explicit OS control

```sh
gesture-scroller run --model hand_landmarker.task --enable-input
```

Opting in still leaves the app **paused**; press **Start** to actually begin
injecting input. The status bar turns green and shows *Running — OS input
armed* so there is no ambiguity. PyAutoGUI's corner fail-safe stays enabled,
and any backend error pauses you immediately.

### Configure

```sh
gesture-scroller config write settings.json     # safe defaults
gesture-scroller config validate settings.json  # validates before use
gesture-scroller run --model hand_landmarker.task --config settings.json --camera 1
```

Settings live in a portable JSON file and are validated on load (bounds,
pinch hysteresis ordering, allowlisted key, camera index). Arming state is
**never** persisted — restarting always returns you to safe dry-run.

## Safety model

- **Two explicit gates before any OS input:** `--enable-input` *and* pressing
  **Start**.
- Starts paused and dry-run. Pausing, changing input mode, losing the hand,
  or a backend error resets transient gesture state.
- Scroll, click, and move are evaluated against the **current** observation;
  there is no background thread that keeps acting after you drop your hand.
- Keyboard output is allowlisted (only optional play/pause) — there is no
  shell-command gesture or destructive shortcut.
- PyAutoGUI's pointer fail-safe is never disabled.

Start with a disposable document or long browser page, keep a physical mouse
and keyboard beside you, and review the
[live-device acceptance checklist](docs/MANUAL_TESTING.md) before treating
it as daily-use software.

## Development

```sh
pip install -e ".[dev]"
pytest -q          # headless unit + integration tests
ruff check .       # lint
ruff format .      # formatting
python -m build    # package wheel/sdist
```

All core logic runs and tests without camera, display, or input packages.
Quality CI (lint, format, tests, demo, build) runs on Python 3.10–3.12 on
Windows and Linux. Passing CI does **not** prove real-camera accuracy or
native OS-input compatibility — that is a separate
[live-device exercise](docs/MANUAL_TESTING.md).

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the reasoning and
[CONTRIBUTING.md](CONTRIBUTING.md) for change discipline.

## License

MIT — see [LICENSE](LICENSE).
