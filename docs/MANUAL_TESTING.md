# Live-device acceptance checklist

Automated tests cover the deterministic gesture pipeline, not the quality of your webcam, lighting, desktop permissions, or physical gestures. Complete this checklist on the machine the application will control before treating it as daily-use software.

## Before starting

- Use a disposable text document or a long browser page, not a payment screen or an application with destructive shortcuts.
- Close other software using the camera.
- Keep a physical keyboard and mouse available. Review the pause and emergency-stop controls in the README.
- Install desktop dependencies and provide the model using the setup instructions.
- On macOS, grant camera and Accessibility permissions as needed. On Linux, check whether the session uses X11 or Wayland; PyAutoGUI does not provide general Wayland input support.

## Preview / dry run

- [ ] Application opens without moving the mouse or scrolling.
- [ ] Paused state and dry-run state are unmistakable.
- [ ] Camera preview is mirrored and tracks one hand reliably.
- [ ] Index-only pose is recognized as pointer movement.
- [ ] Index + middle pose selects scrolling rather than clicking.
- [ ] Moving the scroll pose upward emits positive wheel ticks; downward emits negative ticks.
- [ ] Holding near the scroll anchor stays in the dead zone.
- [ ] Pinching thumb + index produces one click, not repeated clicks while held.
- [ ] Releasing and pinching again produces another click.
- [ ] A closed fist or no hand causes no action.
- [ ] A rotated hand and different camera distances do not produce surprising actions. Record limitations rather than assuming universal recognition.

## Explicitly armed OS control

- [ ] Opt into OS input only after the dry-run checks pass.
- [ ] Pointer movement is usable without jumps to screen edges.
- [ ] Scrolling works in the focused target application at a comfortable speed.
- [ ] Pinch clicks once and never produces an accidental drag.
- [ ] Pause immediately stops new input.
- [ ] The application's Escape shortcut pauses when its window has focus. Do not assume it is a system-wide hotkey.
- [ ] PyAutoGUI's corner fail-safe remains enabled and stops further input.
- [ ] Removing the hand stops scrolling without delayed bursts.
- [ ] Closing the window releases the camera and permits immediate restart.
- [ ] Camera disconnection or read failure pauses input and gives a visible error.

## Evidence to attach to a portfolio release

Record OS/session type, Python version, camera model, dependency versions, settings, and lighting. Attach a short real-camera screen recording showing preview, opt-in arming, bidirectional scroll, one-shot click, and pause. Report observed limitations and measured performance; do not present the deterministic CLI demo as a live-camera demonstration.

## Verification status

These checkboxes are intentionally unchecked. A headless CI run or a successful model import does not complete them.
