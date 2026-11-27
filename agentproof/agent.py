"""The agent loop: the core logic of AgentProof.

The Agent depends only on interfaces (LLMClient, TestRunner, Tool), which
are passed in from outside (dependency injection). It never knows which
model, test runner or storage is used.
"""
from __future__ import annotations

import json
import time
from typing import Callable, Sequence

from .domain import AgentTask, RunResult, Step
from .llm.base import LLMClient
from .prompts import build_system_prompt
from .sandbox import TestRunner
from .tools import Tool, ToolContext, Workspace

StepCallback = Callable[[Step], None]


def parse_action(reply: str) -> dict | None:
    """Return the action dict from the model's reply, or None if it is not valid."""
    try:
        action = json.loads(reply)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(action, dict) or not isinstance(action.get("action"), str):
        return None
    return action


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        runner: TestRunner,
        tools: Sequence[Tool],
        max_steps: int = 10,
        hint: str = "",
        on_step: StepCallback | None = None,
    ):
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.llm = llm
        self.runner = runner
        self.tools = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.hint = hint
        self.on_step = on_step or (lambda step: None)

    def solve(self, task: AgentTask) -> RunResult:
        workspace = Workspace.create(task.start_code)
        context = ToolContext(workspace=workspace, task=task, runner=self.runner)
        messages = [
            {"role": "system", "content": build_system_prompt(list(self.tools.values()))},
            {"role": "user", "content": task.goal + self.hint},
        ]
        steps: list[Step] = []
        tokens = 0
        invalid_replies = 0
        claimed_done = False
        start = time.time()

        for number in range(1, self.max_steps + 1):
            reply = self.llm.chat(messages)
            tokens += reply.tokens
            messages.append({"role": "assistant", "content": reply.text})

            action = parse_action(reply.text)
            if action is None:
                invalid_replies += 1
                step = Step(number, "invalid", result="Error: reply with exactly one JSON object.")
            elif action["action"] == "done":
                claimed_done = True
                step = Step(number, "done", message=str(action.get("message", "")))
            else:
                step = self._run_tool(number, action, context)

            steps.append(step)
            self.on_step(step)
            if claimed_done:
                break
            messages.append({"role": "user", "content": f"Result:\n{step.result}"})

        hidden = self.runner.run(workspace.folder, task.function, task.hidden_tests)
        return RunResult(
            task=task,
            claimed_done=claimed_done,
            hidden=hidden,
            steps=steps,
            invalid_replies=invalid_replies,
            tokens=tokens,
            seconds=round(time.time() - start, 1),
            final_code=workspace.read(),
            own_tests=[t.to_json() for t in context.own_tests],
        )

    def _run_tool(self, number: int, action: dict, context: ToolContext) -> Step:
        name = action["action"]
        tool = self.tools.get(name)
        if tool is None:
            return Step(number, name, result=f"Error: unknown action {name!r}.")
        result = tool.run(action, context)
        content = action.get("content") if name == "write_file" and isinstance(action.get("content"), str) else None
        return Step(number, name, result=result, content=content)
