from types import SimpleNamespace

import pytest


def test_tasks_adapter_uses_video_api_and_monotonic_milliseconds(tmp_path):
    from hand_gesture_scroller.camera import TasksDetector

    calls = []

    class Landmarker:
        @staticmethod
        def create_from_options(options):
            calls.append(options)
            return Landmarker()

        def detect_for_video(self, image, timestamp):
            calls.append(timestamp)
            return SimpleNamespace(hand_landmarks=[[SimpleNamespace(x=0.1, y=0.2, z=0.3)] * 21])

        def close(self):
            calls.append("closed")

    mp = SimpleNamespace(
        tasks=SimpleNamespace(
            BaseOptions=lambda **kw: kw,
            vision=SimpleNamespace(
                HandLandmarker=Landmarker,
                HandLandmarkerOptions=lambda **kw: kw,
                RunningMode=SimpleNamespace(VIDEO="VIDEO"),
            ),
        ),
        Image=lambda **kw: kw,
        ImageFormat=SimpleNamespace(SRGB="SRGB"),
    )
    cv = SimpleNamespace(cvtColor=lambda image, mode: image, COLOR_BGR2RGB=1)
    model = tmp_path / "hand.task"
    model.write_bytes(b"fake; API-shape test only")
    detector = TasksDetector(str(model), mp=mp, cv=cv)
    assert detector.detect("frame", 0) == [(0.1, 0.2, 0.3)] * 21
    detector.detect("frame", 0.0001)
    assert calls[0]["running_mode"] == "VIDEO"
    assert calls[1:3] == [0, 1]
    detector.close()
    assert calls[-1] == "closed"


def test_missing_model_fails_before_optional_imports(tmp_path):
    from hand_gesture_scroller.camera import TasksDetector

    with pytest.raises(ValueError, match="model"):
        TasksDetector(str(tmp_path / "missing"))
