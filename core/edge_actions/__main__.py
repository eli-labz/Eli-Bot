from __future__ import annotations

import argparse
import json

from .config import EdgeActionsConfig
from .runner import EdgeActionRunner


def _parse_inputs(pairs: list[str]) -> dict:
    result = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m core.edge_actions")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_parser = sub.add_parser("run", help="Run an Edge long-horizon task")
    run_parser.add_argument("--task-id", required=True)
    run_parser.add_argument("--input", action="append", default=[], help="key=value input pairs")

    args = parser.parse_args()

    if args.cmd == "run":
        cfg = EdgeActionsConfig.from_env()
        runner = EdgeActionRunner(cfg)
        output = runner.run_task(task_id=args.task_id, inputs=_parse_inputs(args.input))
        print(json.dumps(output, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
