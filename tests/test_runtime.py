from test_actions import FakeDesktop
from test_recognition import landmarks

from hand_gesture_scroller.actions import Dispatcher
from hand_gesture_scroller.config import Config
from hand_gesture_scroller.engine import Engine


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


def test_camera_pipeline_pause_hand_loss_fault_and_cleanup():
    from hand_gesture_scroller.runtime import Session

    desktop = FakeDesktop()
    dispatcher = Dispatcher(backend_factory=lambda: desktop)
    capture = Capture([(True, "frame")] * 7)
    detector = Detector(
        [
            landmarks((0, 1)),
            landmarks((0, 1)),
            landmarks((0, 1), dy=0.2),
            None,
            landmarks((0, 1), dy=0.2),
            landmarks((0,)),
            landmarks((0,)),
        ]
    )
    session = Session(capture, detector, Engine(Config(stability_seconds=0)), dispatcher)
    session.step(0)
    assert desktop.calls == []
    assert session.set_input(True)
    session.toggle_pause()
    session.step(0.1)  # fresh anchor after explicit resume
    session.step(0.3)
    assert desktop.calls == [("scroll", -4)]
    session.step(0.4)  # hand loss
    session.step(0.5)  # re-entry anchors, no burst
    assert len(desktop.calls) == 1
    session.pause()
    session.step(0.6)
    assert len(desktop.calls) == 1
    session.toggle_pause()
    session.step(0.7)
    assert desktop.calls[-1][0] == "move"
    assert session.step(0.8) is None
    assert dispatcher.paused and "Camera read failed" in session.error
    assert capture.released and detector.closed
    session.close()  # idempotent


def test_detector_exception_is_visible_and_releases():
    from hand_gesture_scroller.runtime import Session

    detector = Detector([])
    capture = Capture([(True, "frame")])
    session = Session(capture, detector, Engine(), Dispatcher())
    assert session.step(0) is None
    assert session.error and session.dispatcher.paused
    assert detector.closed and capture.released
