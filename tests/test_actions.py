import sys

import pytest

from hand_gesture_scroller.engine import Action


def test_dispatch_defaults_are_paused_dry_run_without_importing_pyautogui():
    from hand_gesture_scroller.actions import Dispatcher

    dispatcher = Dispatcher()
    assert dispatcher.paused and dispatcher.dry_run
    assert dispatcher.dispatch(Action("scroll", 2)) is False
    dispatcher.resume()
    assert dispatcher.dispatch(Action("scroll", 2)) is True
    assert dispatcher.last_action == Action("scroll", 2)
    assert "pyautogui" not in sys.modules


class FakeDesktop:
    FAILSAFE = True

    def __init__(self):
        self.calls = []

    def size(self):
        return 1000, 800

    def moveTo(self, *args):
        self.calls.append(("move", args))

    def scroll(self, ticks):
        self.calls.append(("scroll", ticks))

    def click(self):
        self.calls.append(("click",))

    def press(self, key):
        self.calls.append(("key", key))


def test_explicit_opt_in_bounded_actions_and_fault_pause():
    from hand_gesture_scroller.actions import Dispatcher

    desktop = FakeDesktop()
    dispatcher = Dispatcher(backend_factory=lambda: desktop)
    dispatcher.enable_input()
    assert dispatcher.paused  # opting in never resumes automatically
    dispatcher.resume()
    assert dispatcher.dispatch(Action("move", (1, 0)))
    assert desktop.calls == [("move", (998, 1))]
    assert dispatcher.dispatch(Action("scroll", -3))
    assert dispatcher.dispatch(Action("click"))
    assert dispatcher.dispatch(Action("key", "playpause")) is False  # opt-in allowlist
    assert dispatcher.paused and "allow" in dispatcher.error
    dispatcher.resume()
    desktop.FAILSAFE = False
    assert not dispatcher.dispatch(Action("click"))
    assert dispatcher.paused and "fail-safe" in dispatcher.error


@pytest.mark.parametrize(
    "action",
    [
        Action("shell", "calc"),
        Action("key", "delete"),
        Action("scroll", 999),
        Action("move", (float("nan"), 0)),
    ],
)
def test_reject_unsafe_actions_even_in_dry_run(action):
    from hand_gesture_scroller.actions import Dispatcher

    dispatcher = Dispatcher()
    dispatcher.resume()
    assert not dispatcher.dispatch(action)
    assert dispatcher.paused and dispatcher.error


def test_backend_exception_and_import_error_pause_without_retry():
    from hand_gesture_scroller.actions import Dispatcher

    def unavailable():
        raise RuntimeError("no desktop")

    dispatcher = Dispatcher(backend_factory=unavailable)
    assert not dispatcher.enable_input()
    assert dispatcher.paused and dispatcher.dry_run and "no desktop" in dispatcher.error
    desktop = FakeDesktop()
    dispatcher = Dispatcher(backend_factory=lambda: desktop, keyboard_action="playpause")
    assert dispatcher.enable_input()
    dispatcher.resume()
    assert dispatcher.dispatch(Action("key", "playpause"))

    def fails():
        raise RuntimeError("corner fail-safe")

    desktop.click = fails
    assert not dispatcher.dispatch(Action("click"))
    assert dispatcher.paused and "corner" in dispatcher.error
