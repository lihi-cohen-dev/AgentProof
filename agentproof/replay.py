"""Replay agent runs step by step from a saved JSON result file.

    python -m agentproof.replay                 # newest result file, all tasks
    python -m agentproof.replay fix_split_bill  # only one task
    python -m agentproof.replay --file agent_results_20261122_185038.json
"""
from __future__ import annotations

import argparse
import glob
import json
import sys


def verdict(run: dict) -> str:
    fixed = run["hidden_passed"] == run["hidden_total"]
    if run["false_success"]:
        return "FALSE SUCCESS - said done, but hidden tests fail"
    if fixed and run["claimed_done"]:
        return "FIXED and said done"
    if fixed:
        return "FIXED, but never said done"
    return "NOT FIXED - ran out of steps"


def format_run(run: dict) -> str:
    lines = [
        "=" * 60,
        f"{run['task']} (run {run.get('run', 1)}): {verdict(run)}",
        f"Hidden tests: {run['hidden_passed']}/{run['hidden_total']}, steps: {run.get('steps', '?')}, "
        f"time: {run.get('seconds', '?')}s, tokens: {run.get('tokens', '?')}",
    ]
    own = run.get("own_tests_list")
    if own is not None:
        name = run["task"].replace("fix_", "")
        lines.append(f"Tests the agent wrote for itself: {len(own)}")
        lines += [f"   {name}{tuple(args)} should return {expected!r}" for args, expected in own]
        lines.append(f"Did one of them check a hidden edge case? {'YES' if run.get('tested_a_hidden_edge_case') else 'no'}")
    lines.append("=" * 60)
    for step in run.get("history", []):
        lines.append(f"\n--- step {step['step']}: {step['action']} ---")
        if step["action"] == "write_file":
            lines.append(step.get("content", "(code was not saved in this results file)"))
        elif step["action"] == "done":
            lines.append(f"Agent says: {step.get('message', '')}")
        else:
            lines.append(step.get("result", ""))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentproof.replay")
    parser.add_argument("task", nargs="?", help="show only this task")
    parser.add_argument("--file", help="result file (default: the newest agent_results_*.json)")
    args = parser.parse_args(argv)

    path = args.file
    if not path:
        files = sorted(glob.glob("agent_results_*.json"))
        if not files:
            print("No agent_results_*.json file found. Run the benchmark first.", file=sys.stderr)
            return 1
        path = files[-1]
    with open(path, encoding="utf-8") as file:
        runs = json.load(file)

    print(f"File: {path}\n")
    for run in runs:
        if not args.task or run["task"] == args.task:
            print(format_run(run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
