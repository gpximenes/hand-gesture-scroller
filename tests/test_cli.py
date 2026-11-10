import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))


def command(*args):
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
    return subprocess.run(
        [sys.executable, "-m", "hand_gesture_scroller", *args],
        text=True,
        capture_output=True,
        env=env,
    )


def test_cli_help_and_demo_are_dependency_free_deterministic():
    assert command("--help").returncode == 0
    first = command("demo")
    assert first.returncode == 0, first.stderr
    assert first.stdout == command("demo").stdout
    events = [json.loads(line) for line in first.stdout.splitlines()]
    assert {event["kind"] for event in events} >= {"move", "scroll", "click"}
    assert all(event["dry_run"] for event in events)


def test_cli_config_write_validate_and_errors(tmp_path):
    target = str(tmp_path / "config.json")
    assert command("config", "write", target).returncode == 0
    assert command("config", "validate", target).returncode == 0
    assert command("config", "write", target).returncode != 0  # no accidental overwrite
    assert command("run", "--model", str(tmp_path / "missing.task")).returncode != 0
