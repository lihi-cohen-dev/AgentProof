"""The actions an agent can take.

Each tool is a small class with one job. A new action is a new Tool
subclass added to the list given to the Agent; the agent loop itself does
not change (open/closed principle).
"""
from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .domain import AgentTask, TestCase, TestReport
from .sandbox import TestRunner

SOLUTION_FILE = "solution.py"


class Workspace:
    """A temporary folder that holds the one file the agent may edit."""

    def __init__(self, folder: str):
        self.folder = folder
        self.path = os.path.join(folder, SOLUTION_FILE)

    @classmethod
    def create(cls, start_code: str) -> "Workspace":
        workspace = cls(tempfile.mkdtemp(prefix="agentproof_"))
        workspace.write(start_code)
        return workspace

    def read(self) -> str:
        with open(self.path, encoding="utf-8") as file:
            return file.read()

    def write(self, content: str) -> None:
        with open(self.path, "w", encoding="utf-8") as file:
            file.write(content)


@dataclass
class ToolContext:
    """What a tool may use while it runs."""

    workspace: Workspace
    task: AgentTask
    runner: TestRunner
    own_tests: list[TestCase] = field(default_factory=list)


class Tool(ABC):
    name: str
    usage: str  # example JSON shown to the model in the system prompt

    @abstractmethod
    def run(self, action: dict, context: ToolContext) -> str:
        """Carry out the action and return the text the agent will see."""


def _check_path(action: dict) -> str | None:
    path = action.get("path", SOLUTION_FILE)
    if path != SOLUTION_FILE:
        return f"Error: you can only access {SOLUTION_FILE}."
    return None


class ReadFileTool(Tool):
    name = "read_file"
    usage = '{"action": "read_file", "path": "solution.py"}'

    def run(self, action: dict, context: ToolContext) -> str:
        return _check_path(action) or context.workspace.read()


class WriteFileTool(Tool):
    name = "write_file"
    usage = '{"action": "write_file", "path": "solution.py", "content": "<the full new file content>"}'

    def run(self, action: dict, context: ToolContext) -> str:
        error = _check_path(action)
        if error:
            return error
        content = action.get("content")
        if not isinstance(content, str):
            return "Error: write_file needs a 'content' string."
        context.workspace.write(content)
        return "File written."


class AddTestTool(Tool):
    name = "add_test"
    usage = '{"action": "add_test", "args": [<arguments for the function>], "expected": <the correct return value>}'

    def run(self, action: dict, context: ToolContext) -> str:
        args = action.get("args")
        if not isinstance(args, list) or "expected" not in action:
            return "Error: add_test needs 'args' (a list) and 'expected'."
        context.own_tests.append(TestCase(args=tuple(args), expected=action["expected"]))
        return f"Test added. You now have {len(context.own_tests)} test(s) of your own."


class RunTestsTool(Tool):
    name = "run_tests"
    usage = '{"action": "run_tests"}'

    def run(self, action: dict, context: ToolContext) -> str:
        groups = [("Given tests", list(context.task.visible_tests))]
        if context.own_tests:
            groups.append(("Your own tests", context.own_tests))
        lines = []
        for label, tests in groups:
            report = context.runner.run(context.workspace.folder, context.task.function, tests)
            lines.append(_format_report(label, report))
        return "\n".join(lines)


def _format_report(label: str, report: TestReport) -> str:
    text = f"{label}: {report.passed}/{report.total} passed."
    if report.error:
        text += f" Error: {report.error}"
    for failure in report.failures:
        text += f"\nFailed: input {failure['input']}, expected {failure['expected']!r}, got {failure['got']}"
    return text


BASE_TOOLS: tuple[type[Tool], ...] = (ReadFileTool, WriteFileTool, RunTestsTool)
EXTRA_TOOLS: dict[str, type[Tool]] = {AddTestTool.name: AddTestTool}
