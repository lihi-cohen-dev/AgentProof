import json

from agentproof.agent import Agent
from agentproof.benchmark import Benchmark
from agentproof.llm import ScriptedClient
from agentproof.metrics import format_table, summarize
from agentproof.prompts import VARIANTS
from agentproof.storage import JsonResultStore, SqliteResultStore
from agentproof.tasks import AGENT_TASKS

LAZY = [{"action": "done", "message": "looks fine"}]


def run_benchmark(store, runner, runs=2, variant="no_hint"):
    agent = Agent(ScriptedClient(LAZY), runner, VARIANTS[variant].build_tools())
    return Benchmark(agent, store, variant).run(AGENT_TASKS, runs)


def test_json_store_writes_the_legacy_format(tmp_path, runner):
    results, path = run_benchmark(JsonResultStore(str(tmp_path)), runner)
    data = json.loads(open(path, encoding="utf-8").read())
    assert len(data) == 6
    for key in ("task", "variant", "run", "hidden_passed", "hidden_total", "false_success", "history"):
        assert key in data[0]
    assert [d["run"] for d in data[:2]] == [1, 2]


def test_two_saves_in_the_same_second_do_not_overwrite(tmp_path, runner):
    store = JsonResultStore(str(tmp_path))
    _, first = run_benchmark(store, runner, runs=1)
    _, second = run_benchmark(store, runner, runs=1)
    assert first != second


def test_sqlite_store_saves_the_same_data(tmp_path, runner):
    store = SqliteResultStore(str(tmp_path / "runs.db"))
    results, _ = run_benchmark(store, runner, variant="edge_cases")
    rows = store.load_all()
    assert len(rows) == len(results) == 6
    assert rows[0] == results[0].to_dict()
    assert {r["variant"] for r in rows} == {"edge_cases"}


def test_summary_counts_false_success(runner, tmp_path):
    results, _ = run_benchmark(JsonResultStore(str(tmp_path)), runner)
    summaries = summarize(results)
    assert [s.task for s in summaries] == [t.name for t in AGENT_TASKS]
    assert all(s.runs == 2 and s.said_done == 2 and s.false_success == 2 and s.fixed == 0 for s in summaries)
    assert "It was wrong 6 of those times." in format_table(summaries)
