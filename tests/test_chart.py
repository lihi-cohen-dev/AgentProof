import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_chart_module():
    spec = importlib.util.spec_from_file_location("make_chart", os.path.join(ROOT, "scripts", "make_chart.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_chart_ignores_demo_runs_with_the_fake_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agent_results_20260101_000000.json").write_text(
        json.dumps([{"task": "t", "variant": "edge_cases", "model": "qwen2.5-coder:7b"}]))
    (tmp_path / "agent_results_20260102_000000.json").write_text(
        json.dumps([{"task": "t", "variant": "edge_cases", "model": "scripted"}]))
    latest = load_chart_module().latest_file_per_variant()
    assert latest["edge_cases"][0] == "agent_results_20260101_000000.json"
