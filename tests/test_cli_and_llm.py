import json

import pytest

from agentproof import cli, replay
from agentproof.llm import LLMError, OllamaClient, ScriptedClient


def test_ollama_client_gives_a_clear_error_when_ollama_is_not_running():
    client = OllamaClient(model="any", url="http://127.0.0.1:9/api/chat", timeout=2)
    with pytest.raises(LLMError, match="Is Ollama running"):
        client.chat([{"role": "user", "content": "hi"}])


def test_scripted_client_repeats_its_last_reply():
    client = ScriptedClient([{"action": "a"}, {"action": "b"}])
    texts = [client.chat([]).text for _ in range(3)]
    assert texts == ['{"action": "a"}', '{"action": "b"}', '{"action": "b"}']


def test_cli_runs_end_to_end_with_the_scripted_model(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["--model", "scripted", "--runs", "1", "--tasks", "fix_decode"])
    out = capsys.readouterr().out
    assert code == 0
    assert "It was wrong 1 of those times." in out
    saved = json.loads(next(tmp_path.glob("agent_results_*.json")).read_text(encoding="utf-8"))
    assert saved[0]["task"] == "fix_decode" and saved[0]["false_success"] is True
    assert saved[0]["model"] == "scripted"

    assert replay.main(["fix_decode"]) == 0
    assert "FALSE SUCCESS" in capsys.readouterr().out


def test_cli_reports_unreachable_model_and_returns_an_error_code(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["--url", "http://127.0.0.1:9/api/chat", "--runs", "1", "--tasks", "fix_decode"])
    assert code == 1
    assert "Is Ollama running" in capsys.readouterr().err
    assert not list(tmp_path.glob("agent_results_*.json"))


def test_replay_handles_old_files_with_missing_fields(tmp_path, capsys):
    old = tmp_path / "old.json"
    old.write_text(json.dumps([{"task": "fix_decode", "hidden_passed": 3, "hidden_total": 5,
                                 "claimed_done": False, "false_success": False}]), encoding="utf-8")
    assert replay.main(["--file", str(old)]) == 0
    assert "NOT FIXED" in capsys.readouterr().out


def test_cli_rejects_unknown_task(capsys):
    assert cli.main(["--model", "scripted", "--tasks", "nope"]) == 2
    assert "Unknown task" in capsys.readouterr().err
