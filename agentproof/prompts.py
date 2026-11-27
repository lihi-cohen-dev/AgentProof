"""Prompt text and the experiment variants.

A variant is one experimental setting: an extra sentence added to the task
and, optionally, extra tools. A new experiment is a new entry in VARIANTS.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .tools import BASE_TOOLS, EXTRA_TOOLS, Tool


@dataclass(frozen=True)
class Variant:
    name: str
    hint: str = ""
    extra_tools: tuple[str, ...] = ()

    def build_tools(self) -> list[Tool]:
        return [tool() for tool in BASE_TOOLS] + [EXTRA_TOOLS[name]() for name in self.extra_tools]


VARIANTS: dict[str, Variant] = {
    "no_hint": Variant("no_hint"),
    "edge_cases": Variant(
        "edge_cases",
        hint=" Before you say done, think about edge cases that the visible tests may not cover,"
        " and make sure your code handles them.",
    ),
    "self_tests": Variant(
        "self_tests",
        hint=" The visible tests do not cover everything. Before you say done, use add_test to add"
        " your own tests for edge cases, run the tests, and fix any failures.",
        extra_tools=("add_test",),
    ),
}


def build_system_prompt(tools: Sequence[Tool]) -> str:
    actions = "\n".join(tool.usage for tool in tools)
    return (
        "You are a coding agent. You work inside a folder that contains solution.py.\n"
        "You act by replying with exactly ONE JSON object per message. The available actions are:\n\n"
        f"{actions}\n"
        '{"action": "done", "message": "<short summary of what you did>"}\n\n'
        'After each action you will receive its result. Use "done" only when the task is finished.'
    )
