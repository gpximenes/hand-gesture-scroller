"""Dependency-free commands; desktop imports happen only for run."""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from .actions import Dispatcher
from .config import Config
from .engine import Engine


def demo():
    """Synthetic landmarks, fixed timestamps, real core, no hardware access."""

    def hand(fingers=(), pinch=False, dy=0):
        points = [(0.5, 0.85, 0)] * 21
        points[4] = (0.08, 0.62, 0)
        for finger, base in enumerate((5, 9, 13, 17)):
            x = 0.32 + finger * 0.12
            ys = (0.65, 0.45, 0.30, 0.15) if finger in fingers else (0.65, 0.50, 0.61, 0.73)
            points[base : base + 4] = [(x, y, 0) for y in ys]
        if pinch:
            points[4] = (points[8][0] + 0.025, points[8][1], 0)
        return [(x, y + dy, z) for x, y, z in points]

    engine = Engine(Config(stability_seconds=0))
    dispatcher = Dispatcher()
    dispatcher.resume()  # simulation only; never enables OS input
    frames = [
        (0, hand((0,))),
        (0.1, hand((0, 1))),
        (0.3, hand((0, 1), dy=0.15)),
        (0.5, hand((0, 1), dy=-0.15)),
        (0.7, hand((0,), pinch=True)),
        (0.9, None),
    ]
    for now, points in frames:
        for action in engine.update(points, now):
            if dispatcher.dispatch(action):
                print(
                    json.dumps(dict(time=now, kind=action.kind, value=action.value, dry_run=True))
                )


def parser():
    result = argparse.ArgumentParser(
        description="Local hand gesture desktop controller; safe by default."
    )
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Deterministic headless simulation; no camera or input deps")
    run = sub.add_parser("run", help="Open native preview, initially paused and dry-run")
    run.add_argument(
        "--model", help="User-supplied MediaPipe hand_landmarker.task; never downloaded"
    )
    run.add_argument("--config", help="Validated JSON settings")
    run.add_argument("--camera", type=int, help="Camera index (default from config, otherwise 0)")
    run.add_argument(
        "--enable-input", action="store_true", help="Explicit OS-input opt-in; still paused"
    )
    config = sub.add_parser("config", help="Write defaults or validate settings")
    actions = config.add_subparsers(dest="operation", required=True)
    write = actions.add_parser("write", help="Write safe defaults")
    write.add_argument("path")
    write.add_argument("--force", action="store_true", help="Replace existing file")
    validate = actions.add_parser("validate", help="Validate a JSON file")
    validate.add_argument("path")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "demo":
            demo()
        elif args.command == "config":
            if args.operation == "write":
                if Path(args.path).exists() and not args.force:
                    raise ValueError("file exists; use --force to replace")
                Config().save(args.path)
                print(f"Wrote {args.path}")
            else:
                Config.load(args.path)
                print(f"Valid configuration: {args.path}")
        else:
            config = Config.load(args.config) if args.config else Config()
            config = replace(
                config,
                model_path=args.model if args.model is not None else config.model_path,
                camera_index=args.camera if args.camera is not None else config.camera_index,
            )
            if not config.model_path or not Path(config.model_path).is_file():
                raise ValueError(
                    "provide an existing hand_landmarker.task with --model PATH or config"
                )
            from .desktop import launch

            launch(config, enable_input=args.enable_input)
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
