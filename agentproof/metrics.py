"""Turning run results into summary numbers. Pure functions, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .domain import RunResult


@dataclass(frozen=True)
class TaskSummary:
    task: str
    runs: int
    fixed: int
    said_done: int
    false_success: int
    wrote_own_tests: int
    avg_steps: float


def summarize(results: Sequence[RunResult]) -> list[TaskSummary]:
    """One summary per task, in the order the tasks first appear."""
    order: list[str] = []
    for r in results:
        if r.task.name not in order:
            order.append(r.task.name)

    summaries = []
    for name in order:
        runs = [r for r in results if r.task.name == name]
        summaries.append(TaskSummary(
            task=name,
            runs=len(runs),
            fixed=sum(r.fixed for r in runs),
            said_done=sum(r.claimed_done for r in runs),
            false_success=sum(r.false_success for r in runs),
            wrote_own_tests=sum(1 for r in runs if r.own_tests),
            avg_steps=sum(len(r.steps) for r in runs) / len(runs),
        ))
    return summaries


def format_table(summaries: Sequence[TaskSummary]) -> str:
    lines = [f"{'task':<16}{'fixed':>7}{'said done':>11}{'FALSE done':>12}{'own tests':>11}{'avg steps':>11}"]
    for s in summaries:
        lines.append(
            f"{s.task:<16}"
            f"{f'{s.fixed}/{s.runs}':>7}"
            f"{f'{s.said_done}/{s.runs}':>11}"
            f"{f'{s.false_success}/{s.runs}':>12}"
            f"{f'{s.wrote_own_tests}/{s.runs}':>11}"
            f"{s.avg_steps:>11.1f}"
        )
    said = sum(s.said_done for s in summaries)
    wrong = sum(s.false_success for s in summaries)
    lines.append("")
    lines.append(f"The agent said 'done' {said} times. It was wrong {wrong} of those times.")
    return "\n".join(lines)
