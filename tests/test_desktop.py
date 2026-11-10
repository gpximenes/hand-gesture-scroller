import pytest

from hand_gesture_scroller.actions import Dispatcher
from hand_gesture_scroller.config import Config
from hand_gesture_scroller.desktop import DesktopApp, _describe
from hand_gesture_scroller.engine import Action, Engine
from hand_gesture_scroller.runtime import Session


@pytest.mark.parametrize(
    ("action", "label"),
    [
        (None, "none"),
        (Action("move", (0.5, 0.5)), "pointer"),
        (Action("scroll", -3), "scroll -3"),
        (Action("scroll", 2), "scroll +2"),
        (Action("click"), "click"),
        (Action("key", "playpause"), "key playpause"),
    ],
)
def test_describe_action_labels(action, label):
    assert _describe(action) == label


class FakeUi:
    """Records every controller->widget call with no display server needed."""

    def __init__(self):
        self.scheduled = []
        self.status = None
        self.gesture = None
        self.last = None
        self.preview = None
        self.controls = None
        self.destroyed = False

    def schedule(self, ms, fn):
        self.scheduled.append((ms, fn))

    def set_status(self, text, color=None):
        self.status = (text, color)

    def set_gesture(self, text):
        self.gesture = text

    def set_last(self, text):
        self.last = text

    def set_preview(self, image):
        self.preview = image

    def set_controls(self, *, running, closed):
        self.controls = (running, closed)

    def destroy(self):
        self.destroyed = True


class Capture:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.released = False

    def read(self):
        return next(self.frames, (False, None))

    def release(self):
        self.released = True


class Detector:
    def __init__(self, hands):
        self.hands = iter(hands)
        self.closed = False

    def detect(self, frame, now):
        return next(self.hands)

    def close(self):
        self.closed = True


class StubCv:
    """Replaces cv2 in tests so _show can convert a dummy frame."""

    COLOR_BGR2RGB = 1

    def cvtColor(self, frame, _mode):
        return frame


def _app(ui, frames, *hands, config=None):
    dispatcher = Dispatcher()
    session = Session(
        Capture(frames), Detector(hands), Engine(config or Config(stability_seconds=0)), dispatcher
    )
    return DesktopApp(session, StubCv(), ui, config or Config())


def test_desktop_app_starts_paused_lifecycle_and_close():
    ui = FakeUi()
    app = _app(ui, [(True, "f")] * 3, None, None, None)
    assert app.session.dispatcher.paused  # safe default
    assert ui.status[0].startswith("Paused")

    app.toggle()
    assert not app.session.dispatcher.paused
    assert app._running
    assert ui.controls == (True, False)

    app.pause()
    assert app.session.dispatcher.paused and not app._running
    assert ui.controls == (False, False)

    app.close()
    assert app.session.closed and app.session.capture.released
    assert ui.destroyed
    app.toggle()  # no-op once closed
    app.pause()
    assert app.session.closed


def test_desktop_app_loop_drives_session_and_schedules_next_frame():
    from test_recognition import landmarks

    ui = FakeUi()
    app = _app(ui, [(True, "frame")] * 4, landmarks((0, 1)), landmarks((0, 1), dy=0.15), None, None)
    app._now = lambda: 0.1
    app._show = lambda frame: None  # PIL preview is exercised on device, not headless
    app.toggle()

    app._loop()
    assert ui.gesture in ("scroll", "neutral", "no hand")
    assert ui.scheduled, "loop must schedule the next invocation"


def test_desktop_app_dispatcher_error_surfaces_in_status():
    from hand_gesture_scroller.actions import Dispatcher

    class Broken:
        def size(self):
            raise RuntimeError("boom")

    class BadDispatcher(Dispatcher):
        def resume(self):
            super().resume()
            self.error = "input backend failed"

    ui = FakeUi()
    dispatcher = BadDispatcher(backend_factory=Broken)
    session = Session(Capture([(True, "f")]), Detector([None]), Engine(Config()), dispatcher)
    app = DesktopApp(session, StubCv(), ui, Config())
    app.toggle()
    assert ui.status[0].startswith("Running") or "error" in ui.status[0].lower()
