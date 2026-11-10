"""Tkinter desktop shell: preview, arming, pause, and dispatch wiring.

Imported only by the ``run`` command. Safe by default: the session starts
paused and in dry-run; OS input requires the explicit ``--enable-input``
opt-in plus an explicit start, and the Escape key pauses when the window
has focus. This module intentionally does not touch a network listener or
a web service - it owns the local webcam and can only control input on the
machine that displays the process.

The controller logic (pause/resume, lifecycle, status) is decoupled from
widgets through a small UI view so it can be exercised headlessly.
"""

import importlib
import time
import tkinter as tk
from tkinter import ttk

from .actions import Dispatcher
from .camera import TasksDetector
from .config import Config
from .engine import Engine
from .runtime import Session

# Tkinter is structurally single-threaded; the frame loop runs on the main
# thread and must never block on a network or a long inference call.
LOOP_MS = 33
STATUS_COLORS = {
    "paused": "#b8860b",  # amber: safe preview
    "running": "#2e7d32",  # green: live
    "error": "#b71c1c",  # red
}


def _require(name, extra="desktop"):
    """Import an optional heavy dependency with an actionable error."""
    try:
        return importlib.import_module(name)
    except ImportError as exc:  # pragma: no cover - exercised only on opt-in paths
        raise RuntimeError(f"the {extra} extra is required: pip install -e '.[{extra}]'") from exc


def build_session(config, enable_input):
    """Construct the full pipeline. Raises instead of silently degrading."""
    cv = _require("cv2")
    dispatcher = Dispatcher(keyboard_action=config.keyboard_action)
    detector = TasksDetector(config.model_path)
    capture = cv.VideoCapture(config.camera_index)
    if not capture.isOpened():
        raise RuntimeError(f"camera {config.camera_index} is not accessible")
    session = Session(
        capture, detector, Engine(config), dispatcher, transform=lambda frame: cv.flip(frame, 1)
    )
    if enable_input:
        session.set_input(True)  # opts in but stays paused; never auto-resumes
    else:
        session.pause()
    return session, cv


class Ui:
    """Widget contract the controller drives; implementations stay thin."""

    controller = None  # set by DesktopApp; bound with type ignore on use

    def schedule(self, ms, fn):
        raise NotImplementedError

    def set_status(self, text, color=None):
        raise NotImplementedError

    def set_gesture(self, text):
        raise NotImplementedError

    def set_last(self, text):
        raise NotImplementedError

    def set_preview(self, image):
        raise NotImplementedError

    def set_controls(self, *, running, closed):
        raise NotImplementedError

    def destroy(self):
        raise NotImplementedError


class TkUi(Ui):
    """Builds the real Tk window and forwards controller state to widgets."""

    def __init__(self, root):
        self.root = root
        self.photo = None  # keep a reference; Tk drops unwrapped images
        self.root.title("Hand Gesture Scroller")
        self.root.resizable(False, False)

        panel = ttk.Frame(self.root, padding=8)
        panel.pack(fill=tk.BOTH, expand=True)

        self.preview = ttk.Label(panel)
        self.preview.pack(fill=tk.BOTH, expand=True)

        bar = ttk.Frame(panel)
        bar.pack(fill=tk.X, pady=(8, 0))
        self.status = ttk.Label(bar, text="", anchor=tk.W)
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_start = ttk.Button(bar, text="Start")
        self.btn_start.pack(side=tk.RIGHT, padx=(8, 0))
        self.btn_stop = ttk.Button(bar, text="Stop", state=tk.DISABLED)
        self.btn_stop.pack(side=tk.RIGHT)

        gesture = ttk.Frame(panel)
        gesture.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(gesture, text="Gesture:").pack(side=tk.LEFT)
        self.gesture = ttk.Label(gesture, text="no hand", anchor=tk.W)
        self.gesture.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(gesture, text="Last action:").pack(side=tk.LEFT)
        self.last = ttk.Label(gesture, text="none", anchor=tk.E)
        self.last.pack(side=tk.LEFT)

    def schedule(self, ms, fn):
        self.root.after(ms, fn)

    def set_status(self, text, color=None):
        self.status.config(text=text, foreground=color)

    def set_gesture(self, text):
        self.gesture.config(text=text)

    def set_last(self, text):
        self.last.config(text=text)

    def set_preview(self, image):
        self.photo = image
        self.preview.config(image=image)

    def set_controls(self, *, running, closed):
        self.btn_start.config(
            text="Pause" if running else "Start",
            state=tk.DISABLED if closed else tk.NORMAL,
            command=self.controller.toggle,
        )
        self.btn_stop.config(
            state=tk.DISABLED if closed or not running else tk.NORMAL, command=self.controller.pause
        )

    def destroy(self):
        self.root.destroy()


class DesktopApp:
    """Owns the UI view and drives a :class:`Session` on the event loop."""

    def __init__(self, session, cv, ui, config=None, now=None):
        self.session = session
        self.cv = cv
        self.ui = ui
        self.config = config or Config()
        self._now = now or time.monotonic
        self._running = False
        self.ui.controller = self
        self._update_ui()

    def toggle(self):
        if self.session.closed:
            return
        if self.session.dispatcher.paused:
            self.session.engine.reset()
            self.session.dispatcher.resume()
            self._running = True
        else:
            self.pause()
        self._update_ui()

    def pause(self):
        self.session.pause()
        self._running = False
        self._update_ui()

    def _update_ui(self):
        dispatcher = self.session.dispatcher
        if dispatcher.error:
            text, color = f"Error: {dispatcher.error}", STATUS_COLORS["error"]
        elif not self._running:
            text, color = (
                "Paused — safe preview (dry-run: %s)" % ("yes" if dispatcher.dry_run else "no"),
                STATUS_COLORS["paused"],
            )
        else:
            mode = "input disabled" if dispatcher.dry_run else "OS input armed"
            text, color = f"Running — {mode}", STATUS_COLORS["running"]
        self.ui.set_status(text, color)
        self.ui.set_controls(running=self._running, closed=self.session.closed)

    def _loop(self):
        if self.session.closed:
            return
        now = self._now()
        frame = self.session.step(now)
        if frame is not None:
            self._show(frame)
        self.ui.set_gesture(self.session.engine.gesture or "no hand")
        self.ui.set_last(_describe(self.session.dispatcher.last_action))
        self._update_ui()
        self.ui.schedule(LOOP_MS, self._loop)

    def _show(self, frame):
        """Convert a BGR frame to a Tk photo and forward it to the UI."""
        image = self.cv.cvtColor(frame, self.cv.COLOR_BGR2RGB)
        from PIL import Image, ImageTk

        self.ui.set_preview(ImageTk.PhotoImage(image=Image.fromarray(image)))

    def close(self):
        if self.session.closed:
            return
        self.session.close()
        self._running = False
        self._update_ui()
        self.ui.destroy()


def _describe(action):
    """Human label for the last dispatched action (or 'none')."""
    if action is None:
        return "none"
    if action.kind == "move":
        return "pointer"
    if action.kind == "scroll":
        return f"scroll {action.value:+d}"
    if action.kind == "click":
        return "click"
    return f"key {action.value}"


def launch(config, enable_input=False):
    """Entry point for the ``gesture-scroller run`` command.

    Keyboard-interrupt and window-close both tear the pipeline down cleanly.
    Cleanup happens in order and the process exits once the window is gone.
    """
    session, cv = build_session(config, enable_input)
    root = tk.Tk()
    ui = TkUi(root)
    root.protocol("WM_DELETE_WINDOW", lambda: None)  # replaced below
    app = DesktopApp(session, cv, ui, config)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.bind("<Escape>", lambda _event: app.pause())
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.close()
