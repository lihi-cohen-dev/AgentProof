"""The test runner must survive anything the agent's code does."""
from agentproof.domain import TestCase
from agentproof.sandbox import SubprocessTestRunner
from agentproof.tools import Workspace

ADD_TESTS = [TestCase((2, 3), 5), TestCase((-1, 1), 0)]


def run_code(code, runner, tests=ADD_TESTS, function="add"):
    workspace = Workspace.create(code)
    return runner.run(workspace.folder, function, tests)


def test_correct_code_passes(runner):
    report = run_code("def add(a, b):\n    return a + b\n", runner)
    assert report.all_passed and report.passed == 2


def test_wrong_code_reports_each_failure(runner):
    report = run_code("def add(a, b):\n    return a - b\n", runner)
    assert report.passed == 0
    assert report.failures[0] == {"input": [2, 3], "expected": 5, "got": "-1"}


def test_syntax_error_is_reported_not_raised(runner):
    report = run_code("def add(a, b)\n    return a + b\n", runner)
    assert report.passed == 0 and "could not load solution.py" in report.error


def test_missing_function_is_reported(runner):
    report = run_code("def plus(a, b):\n    return a + b\n", runner)
    assert "could not load" in report.error


def test_exception_inside_function_counts_as_failure(runner):
    report = run_code("def add(a, b):\n    raise ValueError('nope')\n", runner)
    assert report.passed == 0 and "ValueError" in report.failures[0]["got"]


def test_print_in_agent_code_does_not_break_the_report(runner):
    report = run_code("print('hello')\ndef add(a, b):\n    print('x')\n    return a + b\n", runner)
    assert report.all_passed


def test_infinite_loop_times_out():
    report = run_code("def add(a, b):\n    while True:\n        pass\n", SubprocessTestRunner(timeout=1))
    assert report.passed == 0 and "timed out" in report.error


def test_sys_exit_in_agent_code_is_contained(runner):
    report = run_code("import sys\nsys.exit(3)\n", runner)
    assert report.passed == 0 and "SystemExit" in report.error
