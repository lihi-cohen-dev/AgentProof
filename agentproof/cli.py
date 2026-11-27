"""Command line entry point. This is the only place that picks concrete classes.

    python -m agentproof --variant self_tests --runs 5 --store sqlite
"""
from __future__ import annotations

import argparse
import sys

from .agent import Agent
from .benchmark import Benchmark
from .llm import LLMClient, LLMError, OllamaClient, ScriptedClient
from .metrics import format_table, summarize
from .prompts import VARIANTS
from .sandbox import SubprocessTestRunner
from .storage import STORES
from .tasks import AGENT_TASKS, get_tasks

DEMO_REPLIES = [
    {"action": "read_file", "path": "solution.py"},
    {"action": "run_tests"},
    {"action": "done", "message": "Looks fine to me."},
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentproof", description="Measure false success of AI coding agents.")
    parser.add_argument("--model", default="qwen2.5-coder:7b",
                        help="Ollama model name, or 'scripted' for a fake demo agent (no model needed)")
    parser.add_argument("--url", default="http://localhost:11434/api/chat", help="Ollama chat URL")
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="no_hint", help="experiment to run")
    parser.add_argument("--runs", type=int, default=5, help="runs per task")
    parser.add_argument("--max-steps", type=int, default=10, help="step limit per run")
    parser.add_argument("--timeout", type=float, default=10, help="seconds allowed for each test run")
    parser.add_argument("--store", choices=sorted(STORES), default="json", help="where to save results")
    parser.add_argument("--tasks", nargs="*", metavar="TASK",
                        help=f"only these tasks ({', '.join(t.name for t in AGENT_TASKS)})")
    return parser


def build_llm(args: argparse.Namespace) -> LLMClient:
    if args.model == "scripted":
        return ScriptedClient(DEMO_REPLIES)
    return OllamaClient(model=args.model, url=args.url)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tasks = get_tasks(args.tasks)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    variant = VARIANTS[args.variant]
    agent = Agent(
        llm=build_llm(args),
        runner=SubprocessTestRunner(timeout=args.timeout),
        tools=variant.build_tools(),
        max_steps=args.max_steps,
        hint=variant.hint,
        on_step=lambda step: print(f"    step {step.number}: {step.action}"),
    )
    benchmark = Benchmark(agent, STORES[args.store](), variant.name, model=args.model, on_progress=print)

    try:
        results, location = benchmark.run(tasks, args.runs)
    except LLMError as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped. Nothing was saved.", file=sys.stderr)
        return 130

    print(f"\nSaved results to {location}\n")
    print(format_table(summarize(results)))
    return 0
