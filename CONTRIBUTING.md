# Contributing

## Local checks

Use Python 3.11 (recommended) or another version in the CI matrix. The core has no webcam, display, or input-control dependency.

```sh
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m build
```

On Linux/macOS use `.venv/bin/python` instead. To exercise the camera UI, install `.[desktop,dev]` and provide the MediaPipe model as described in the README.

## Change discipline

1. Open an issue or describe the behavior and safety implications in a pull request.
2. Add a failing regression test, implement the smallest change, then run the full suite.
3. Keep landmark recognition and temporal policy independent of hardware. Inject camera/input adapters in integration tests; never move a contributor's actual mouse during tests.
4. Never disable PyAutoGUI's fail-safe, silently enable OS input, persist an armed state, or introduce background action loops.
5. Update configuration docs and the manual acceptance checklist when behavior changes.
6. Do not commit virtual environments, camera frames, user settings, models, or generated build artifacts.

CI checks Python 3.10–3.12 on Windows and Linux for the **headless core**. Passing CI is not evidence of real-camera recognition accuracy or native OS input compatibility. Include live-device evidence separately.
