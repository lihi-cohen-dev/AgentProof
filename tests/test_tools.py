import pytest

from agentproof.tools import AddTestTool, ReadFileTool, RunTestsTool, ToolContext, Workspace, WriteFileTool

from conftest import REFERENCE_SOLUTIONS


@pytest.fixture
def context(split_bill_task, runner):
    return ToolContext(workspace=Workspace.create(split_bill_task.start_code), task=split_bill_task, runner=runner)


def test_read_file_returns_the_code(context, split_bill_task):
    assert ReadFileTool().run({"action": "read_file", "path": "solution.py"}, context) == split_bill_task.start_code


@pytest.mark.parametrize("path", ["../secret.txt", "/etc/passwd", "other.py"])
def test_tools_refuse_any_other_path(context, path):
    assert "only access solution.py" in ReadFileTool().run({"path": path}, context)
    assert "only access solution.py" in WriteFileTool().run({"path": path, "content": "x"}, context)


def test_write_file_replaces_the_code(context):
    assert WriteFileTool().run({"path": "solution.py", "content": "x = 1\n"}, context) == "File written."
    assert context.workspace.read() == "x = 1\n"


def test_write_file_needs_text_content(context):
    assert "needs a 'content' string" in WriteFileTool().run({"path": "solution.py", "content": 5}, context)


def test_run_tests_shows_only_visible_tests(context):
    result = RunTestsTool().run({}, context)
    assert result.startswith("Given tests: 1/2 passed.")
    assert "[0, 2]" not in result  # a hidden edge case must never leak


def test_add_test_validates_input(context):
    assert "needs 'args'" in AddTestTool().run({"args": "bad"}, context)
    assert "needs 'args'" in AddTestTool().run({"args": [1, 2]}, context)
    assert context.own_tests == []


def test_own_tests_run_together_with_given_tests(context):
    AddTestTool().run({"args": [0, 2], "expected": [0, 0]}, context)
    context.workspace.write(REFERENCE_SOLUTIONS["fix_split_bill"])
    result = RunTestsTool().run({}, context)
    assert "Given tests: 2/2 passed." in result
    assert "Your own tests: 1/1 passed." in result
