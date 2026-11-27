"""The task data must be correct, or every result would be meaningless."""
import pytest

from agentproof.tasks import AGENT_TASKS, get_tasks
from agentproof.tools import Workspace

from conftest import REFERENCE_SOLUTIONS


@pytest.mark.parametrize("task", AGENT_TASKS, ids=lambda t: t.name)
def test_buggy_start_code_fails_hidden_tests(task, runner):
    workspace = Workspace.create(task.start_code)
    report = runner.run(workspace.folder, task.function, task.hidden_tests)
    assert not report.all_passed


@pytest.mark.parametrize("task", AGENT_TASKS, ids=lambda t: t.name)
def test_reference_solution_passes_all_tests(task, runner):
    workspace = Workspace.create(REFERENCE_SOLUTIONS[task.name])
    assert runner.run(workspace.folder, task.function, task.visible_tests).all_passed
    assert runner.run(workspace.folder, task.function, task.hidden_tests).all_passed


@pytest.mark.parametrize("task", AGENT_TASKS, ids=lambda t: t.name)
def test_hidden_tests_include_edge_cases_the_agent_cannot_see(task):
    assert task.edge_case_inputs()


def test_get_tasks_filters_by_name():
    assert [t.name for t in get_tasks(["fix_decode"])] == ["fix_decode"]
    assert len(get_tasks()) == len(AGENT_TASKS)


def test_get_tasks_rejects_unknown_names():
    with pytest.raises(ValueError, match="Unknown task"):
        get_tasks(["no_such_task"])
