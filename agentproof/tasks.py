"""The bug-fixing tasks. Adding a task means adding one AgentTask here."""
from __future__ import annotations

from .domain import AgentTask, TestCase


def _cases(pairs) -> tuple[TestCase, ...]:
    return tuple(TestCase(args=args, expected=expected) for args, expected in pairs)


AGENT_TASKS: tuple[AgentTask, ...] = (
    AgentTask(
        name="fix_split_bill",
        goal="The function split_bill in solution.py has a bug. Fix it.",
        function="split_bill",
        start_code=(
            "def split_bill(total, people):\n"
            "    if total < people:\n"
            "        raise ValueError('total is too small')\n"
            "    base = total // people\n"
            "    return [base] * people\n"
        ),
        visible_tests=_cases([
            ((100, 4), [25, 25, 25, 25]),
            ((10, 4), [3, 3, 2, 2]),
        ]),
        hidden_tests=_cases([
            ((100, 3), [34, 33, 33]),
            ((10, 4), [3, 3, 2, 2]),
            ((0, 2), [0, 0]),
            ((5, 5), [1, 1, 1, 1, 1]),
            ((1, 3), [1, 0, 0]),
        ]),
    ),
    AgentTask(
        name="fix_decode",
        goal="The function decode in solution.py has a bug. Fix it.",
        function="decode",
        start_code=(
            "def decode(s):\n"
            "    result = ''\n"
            "    i = 0\n"
            "    while i < len(s):\n"
            "        letter = s[i]\n"
            "        i += 1\n"
            "        count = 1\n"
            "        if i < len(s) and s[i].isdigit():\n"
            "            count = int(s[i])\n"
            "            i += 1\n"
            "        result += letter * count\n"
            "    return result\n"
        ),
        visible_tests=_cases([
            (("a3b2",), "aaabb"),
            (("x12",), "xxxxxxxxxxxx"),
        ]),
        hidden_tests=_cases([
            (("a3b2",), "aaabb"),
            (("x12",), "xxxxxxxxxxxx"),
            (("abc",), "abc"),
            (("",), ""),
            (("a1b10",), "abbbbbbbbbb"),
        ]),
    ),
    AgentTask(
        name="fix_next_bus",
        goal="The function next_bus in solution.py has a bug. Fix it.",
        function="next_bus",
        start_code=(
            "def next_bus(times, now):\n"
            "    # times: list of 'HH:MM' strings. Return the first departure at or after now.\n"
            "    # If there are no more departures today, return the earliest one (tomorrow).\n"
            "    for t in times:\n"
            "        if t >= now:\n"
            "            return t\n"
            "    return times[0]\n"
        ),
        visible_tests=_cases([
            ((["08:15", "07:30", "09:00"], "07:00"), "07:30"),
            ((["07:30", "08:15", "09:00"], "09:01"), "07:30"),
        ]),
        hidden_tests=_cases([
            ((["08:15", "07:30", "09:00"], "08:00"), "08:15"),
            ((["08:15", "07:30", "09:00"], "08:15"), "08:15"),
            ((["08:15", "07:30", "09:00"], "09:01"), "07:30"),
            ((["23:59"], "00:00"), "23:59"),
            ((["10:05", "10:50", "10:15"], "10:06"), "10:15"),
            ((["08:15", "07:30", "09:00"], "07:00"), "07:30"),
        ]),
    ),
)


def get_tasks(names: list[str] | None = None) -> list[AgentTask]:
    """Return all tasks, or only the ones whose names are given."""
    if not names:
        return list(AGENT_TASKS)
    by_name = {task.name: task for task in AGENT_TASKS}
    unknown = [n for n in names if n not in by_name]
    if unknown:
        raise ValueError(f"Unknown task(s): {', '.join(unknown)}. Known: {', '.join(by_name)}")
    return [by_name[n] for n in names]
