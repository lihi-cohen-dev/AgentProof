"""Running tests on the agent's code, kept away from the benchmark process."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Sequence

from .domain import TestCase, TestReport

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox_worker.py")


class TestRunner(ABC):
    """Runs test cases against the solution.py found in a folder."""

    __test__ = False

    @abstractmethod
    def run(self, folder: str, function: str, tests: Sequence[TestCase]) -> TestReport:
        ...


class SubprocessTestRunner(TestRunner):
    """Runs the tests in a separate Python process with a time limit.

    A crash, an infinite loop or a stray print in the agent's code cannot
    take down the benchmark. This is process isolation, not a security
    sandbox: a container-based runner can replace this class later.
    """

    def __init__(self, timeout: float = 10):
        self.timeout = timeout

    def run(self, folder: str, function: str, tests: Sequence[TestCase]) -> TestReport:
        tests_json = json.dumps([t.to_json() for t in tests])
        try:
            completed = subprocess.run(
                [sys.executable, "-I", WORKER, folder, function, tests_json],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return TestReport(0, len(tests), error=f"timed out after {self.timeout:g}s")

        lines = completed.stdout.strip().splitlines()
        if not lines:
            detail = completed.stderr.strip().splitlines()[-1:] or ["no output"]
            return TestReport(0, len(tests), error=f"test worker failed: {detail[0]}")
        try:
            data = json.loads(lines[-1])
        except json.JSONDecodeError:
            return TestReport(0, len(tests), error="test worker returned invalid output")
        return TestReport(
            passed=data["passed"],
            total=data["total"],
            failures=data.get("failures", []),
            error=data.get("error", ""),
        )
