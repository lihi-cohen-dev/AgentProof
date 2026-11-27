import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentproof.sandbox import SubprocessTestRunner  # noqa: E402
from agentproof.tasks import AGENT_TASKS  # noqa: E402

# Correct solutions, used to prove that the hidden tests themselves are right.
REFERENCE_SOLUTIONS = {
    "fix_split_bill": (
        "def split_bill(total, people):\n"
        "    base, extra = divmod(total, people)\n"
        "    return [base + 1] * extra + [base] * (people - extra)\n"
    ),
    "fix_decode": (
        "import re\n"
        "def decode(s):\n"
        "    return ''.join(c * (int(n) if n else 1) for c, n in re.findall(r'([a-zA-Z])(\\d*)', s))\n"
    ),
    "fix_next_bus": (
        "def next_bus(times, now):\n"
        "    ordered = sorted(times)\n"
        "    for t in ordered:\n"
        "        if t >= now:\n"
        "            return t\n"
        "    return ordered[0]\n"
    ),
}


@pytest.fixture
def runner():
    return SubprocessTestRunner(timeout=5)


@pytest.fixture
def split_bill_task():
    return next(t for t in AGENT_TASKS if t.name == "fix_split_bill")
