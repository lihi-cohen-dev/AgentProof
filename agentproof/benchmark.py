"""Runs an agent on every task several times and saves the results."""
from __future__ import annotations

import dataclasses
from typing import Callable, Sequence

from .agent import Agent
from .domain import AgentTask, RunResult
from .storage import ResultStore

ProgressCallback = Callable[[str], None]


class Benchmark:
    def __init__(self, agent: Agent, store: ResultStore, variant: str,
                 model: str = "", on_progress: ProgressCallback | None = None):
        self.agent = agent
        self.model = model
        self.store = store
        self.variant = variant
        self.on_progress = on_progress or (lambda text: None)

    def run(self, tasks: Sequence[AgentTask], runs_per_task: int) -> tuple[list[RunResult], str]:
        if runs_per_task < 1:
            raise ValueError("runs_per_task must be at least 1")
        results = []
        for task in tasks:
            for number in range(1, runs_per_task + 1):
                self.on_progress(f"Agent on {task.name} (run {number}/{runs_per_task})...")
                result = dataclasses.replace(self.agent.solve(task), variant=self.variant, run=number, model=self.model)
                results.append(result)
                self.on_progress(
                    f"  hidden tests {result.hidden.passed}/{result.hidden.total}, "
                    f"said done: {result.claimed_done}, steps: {len(result.steps)}, {result.seconds}s"
                )
        location = self.store.save(results)
        return results, location
