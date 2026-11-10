# Prototype review

This review describes the original `master` snapshot (`ea3bd28`), not the redesigned implementation.

## Findings

| Priority | Finding | Evidence / impact |
| --- | --- | --- |
| High | No explicit input arming or pause gate | `Main.py` starts camera-driven mouse movement immediately on launch. |
| High | Scroll actions outlive the observed gesture | `ScrollController.scroll` launches a daemon thread running on wall-clock time. Hand loss and application shutdown do not cancel it. |
| High | Race in scroll activation | `active` is set inside the worker, rather than before thread startup. Multiple workers can be created. |
| Medium | Missing runtime dependency | `Main.py` imports `pyautogui`, but `requirements.txt` does not declare it. |
| Medium | Conflicting OpenCV distributions | Requirements include both `opencv-python` and `opencv-contrib-python`, which provide the same `cv2` namespace. |
| Medium | Scale-dependent gesture recognition | Fixed pixel pinch thresholds change meaning with frame resolution and distance from the camera. |
| Medium | Coupled application and hardware | Importing the monolithic module requires GUI, camera, inference, and input packages, preventing isolated headless tests. |
| Medium | Undocumented setup requirements | The README contains a malformed clone command, references a nonexistent entry point, promises controls that do not exist, and mislabels wheel ticks as pixels. |
| Medium | Generated artifacts committed | The snapshot tracks 6,491 files, including 6,475 virtual-environment files and nine root bytecode files. |
| Medium | No automated quality gates | No application test suite, package metadata, or CI workflow. |
| Low | GUI lifecycle and configuration issues | Sliders may reinitialize inference during widget creation; editable entries are not consistently applied or validated; a failed frame read leaves the app running silently. |

## Redesign criteria

- Separate landmark recognition, temporal gesture state, action dispatch, and hardware/UI adapters.
- Default to paused, dry-run operation; require explicit consent before OS input.
- Avoid background action loops; every action must be justified by a current valid observation.
- Test direction, dead zones, rate limits, pinch release, hand loss, pause, and malformed configuration.
- Keep the project importable and demonstrable without camera or desktop dependencies.
- Make platform limitations explicit and distinguish simulated verification from live-camera evidence.
- Replace tracked environments with reproducible package extras and CI.

## Scope boundary

This work does not rewrite Git history, claim certified accessibility support, or establish real-camera accuracy or cross-platform input compatibility without hardware tests. Removing the environment in a new commit cleans the current tree; old blobs remain in history.
