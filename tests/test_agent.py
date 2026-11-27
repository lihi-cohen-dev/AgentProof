"""The agent loop, driven by a fake model so no real LLM is needed."""
import pytest

from agentproof.agent import Agent, parse_action
from agentproof.llm import ScriptedClient
from agentproof.prompts import VARIANTS

from conftest import REFERENCE_SOLUTIONS

FIX = REFERENCE_SOLUTIONS["fix_split_bill"]


def make_agent(replies, runner, variant="no_hint", max_steps=10):
    v = VARIANTS[variant]
    llm = ScriptedClient(replies)
    return Agent(llm=llm, runner=runner, tools=v.build_tools(), max_steps=max_steps, hint=v.hint), llm


def test_careful_agent_fixes_the_bug(split_bill_task, runner):
    agent, _ = make_agent([
        {"action": "read_file", "path": "solution.py"},
        {"action": "write_file", "path": "solution.py", "content": FIX},
        {"action": "run_tests"},
        {"action": "done", "message": "fixed"},
    ], runner)
    result = agent.solve(split_bill_task)
    assert result.fixed and result.claimed_done and not result.false_success
    assert [s.action for s in result.steps] == ["read_file", "write_file", "run_tests", "done"]
    assert result.steps[1].content == FIX


def test_agent_that_says_done_without_fixing_is_a_false_success(split_bill_task, runner):
    agent, _ = make_agent([{"action": "done", "message": "looks fine"}], runner)
    result = agent.solve(split_bill_task)
    assert result.claimed_done and not result.fixed and result.false_success


def test_stuck_agent_stops_at_the_step_limit(split_bill_task, runner):
    agent, llm = make_agent([{"action": "run_tests"}], runner, max_steps=4)
    result = agent.solve(split_bill_task)
    assert len(result.steps) == 4 and len(llm.calls) == 4
    assert not result.claimed_done and not result.false_success
    assert result.repeated_actions == 3


def test_invalid_replies_are_counted_and_the_agent_continues(split_bill_task, runner):
    agent, _ = make_agent(["not json", '["a list"]', {"action": "done"}], runner)
    result = agent.solve(split_bill_task)
    assert result.invalid_replies == 2 and result.claimed_done


def test_unknown_action_gets_an_error_message(split_bill_task, runner):
    agent, llm = make_agent([{"action": "fly"}, {"action": "done"}], runner)
    agent.solve(split_bill_task)
    assert "unknown action 'fly'" in llm.calls[1][-1]["content"]


def test_add_test_is_only_available_in_the_self_tests_variant(split_bill_task, runner):
    replies = [{"action": "add_test", "args": [0, 2], "expected": [0, 0]}, {"action": "done"}]
    no_hint_agent, llm = make_agent(replies, runner)
    no_hint_agent.solve(split_bill_task)
    assert "unknown action 'add_test'" in llm.calls[1][-1]["content"]

    self_tests_agent, _ = make_agent(replies, runner, variant="self_tests")
    result = self_tests_agent.solve(split_bill_task)
    assert result.own_tests == [[[0, 2], [0, 0]]]
    assert result.to_dict()["tested_a_hidden_edge_case"] is True


def test_hint_and_tools_appear_in_the_prompt(split_bill_task, runner):
    agent, llm = make_agent([{"action": "done"}], runner, variant="self_tests")
    agent.solve(split_bill_task)
    system, user = llm.calls[0][0]["content"], llm.calls[0][1]["content"]
    assert '"add_test"' in system and "use add_test" in user


def test_hidden_tests_never_appear_in_the_conversation(split_bill_task, runner):
    agent, llm = make_agent([{"action": "read_file"}, {"action": "run_tests"}, {"action": "done"}], runner)
    agent.solve(split_bill_task)
    conversation = str(llm.calls)
    assert "[34, 33, 33]" not in conversation and "[1, 0, 0]" not in conversation


def test_agent_sees_the_full_test_output(split_bill_task, runner):
    long_bad_code = "def split_bill(total, people):\n    return ['x' * 200] * people\n"
    agent, llm = make_agent([
        {"action": "write_file", "path": "solution.py", "content": long_bad_code},
        {"action": "run_tests"},
        {"action": "done"},
    ], runner)
    result = agent.solve(split_bill_task)
    seen = llm.calls[2][-1]["content"]
    assert len(seen) > 300 and seen.count("Failed:") == 2
    assert len(result.to_dict()["history"][1]["result"]) <= 300


def test_on_step_callback_gets_every_step(split_bill_task, runner):
    seen = []
    agent = Agent(ScriptedClient([{"action": "run_tests"}, {"action": "done"}]), runner,
                  VARIANTS["no_hint"].build_tools(), on_step=seen.append)
    agent.solve(split_bill_task)
    assert [s.action for s in seen] == ["run_tests", "done"]


@pytest.mark.parametrize("reply, expected", [
    ('{"action": "run_tests"}', {"action": "run_tests"}),
    ("not json", None),
    ('{"no_action": 1}', None),
    ('{"action": 5}', None),
])
def test_parse_action(reply, expected):
    assert parse_action(reply) == expected


def test_max_steps_must_be_positive(runner):
    with pytest.raises(ValueError):
        Agent(ScriptedClient([{"action": "done"}]), runner, [], max_steps=0)
