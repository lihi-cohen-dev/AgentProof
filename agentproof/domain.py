"""Plain data objects shared by every part of AgentProof.

Nothing in this module talks to a model, the file system or a database,
so it can be imported anywhere without side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TestCase:
    """One call to the function under test and the value it must return."""

    __test__ = False  # tell pytest this is not a test class

    args: tuple
    expected: Any

    def to_json(self) -> list:
        return [list(self.args), self.expected]


@dataclass(frozen=True)
class AgentTask:
    """A bug-fixing task: buggy starting code plus visible and hidden tests."""

    name: str
    goal: str
    function: str
    start_code: str
    visible_tests: tuple[TestCase, ...]
    hidden_tests: tuple[TestCase, ...]

    def edge_case_inputs(self) -> list[list]:
        """Inputs that appear only in the hidden tests."""
        visible = [list(t.args) for t in self.visible_tests]
        return [list(t.args) for t in self.hidden_tests if list(t.args) not in visible]


@dataclass
class TestReport:
    """The outcome of running a list of test cases against solution.py."""

    __test__ = False

    passed: int
    total: int
    failures: list[dict] = field(default_factory=list)
    error: str = ""

    @property
    def all_passed(self) -> bool:
        return not self.error and self.passed == self.total


@dataclass
class Step:
    """One action the agent took, and what it saw as a result."""

    number: int
    action: str
    result: str = ""
    content: str | None = None
    message: str | None = None

    def to_dict(self) -> dict:
        data = {"step": self.number, "action": self.action}
        if self.action == "done":
            data["message"] = self.message or ""
            return data
        data["result"] = self.result[:300]  # the agent saw the full text; files keep a short version
        if self.content is not None:
            data["content"] = self.content
        return data


@dataclass
class RunResult:
    """Everything measured in one agent run on one task."""

    task: AgentTask
    claimed_done: bool
    hidden: TestReport
    steps: list[Step]
    invalid_replies: int
    tokens: int
    seconds: float
    final_code: str
    own_tests: list[list] = field(default_factory=list)
    variant: str = "no_hint"
    run: int = 1
    model: str = ""

    @property
    def fixed(self) -> bool:
        return self.hidden.all_passed

    @property
    def false_success(self) -> bool:
        """The agent said it was done, but the hidden tests still fail."""
        return self.claimed_done and not self.fixed

    @property
    def repeated_actions(self) -> int:
        """How many times the agent repeated exactly the step before it."""
        return sum(
            1
            for before, after in zip(self.steps, self.steps[1:])
            if before.action == after.action and before.result == after.result
        )

    def to_dict(self) -> dict:
        """Flat dictionary, compatible with the result files of earlier versions."""
        actions = [s.action for s in self.steps]
        edge_inputs = self.task.edge_case_inputs()
        return {
            "task": self.task.name,
            "variant": self.variant,
            "model": self.model,
            "run": self.run,
            "claimed_done": self.claimed_done,
            "hidden_passed": self.hidden.passed,
            "hidden_total": self.hidden.total,
            "false_success": self.false_success,
            "ran_tests": "run_tests" in actions,
            "own_tests": len(self.own_tests),
            "own_tests_list": self.own_tests,
            "tested_a_hidden_edge_case": any(args in edge_inputs for args, _ in self.own_tests),
            "steps": len(self.steps),
            "invalid_replies": self.invalid_replies,
            "repeated_actions": self.repeated_actions,
            "tokens": self.tokens,
            "seconds": self.seconds,
            "final_code": self.final_code,
            "history": [s.to_dict() for s in self.steps],
        }
