import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime

from agent_tasks import AGENT_TASKS

MODEL = "qwen2.5-coder:7b"
URL = "http://localhost:11434/api/chat"
RUNS_PER_TASK = 5
MAX_STEPS = 10
VARIANT = "self_tests"
HINT = " The visible tests do not cover everything. Before you say done, use add_test to add your own tests for edge cases, run the tests, and fix any failures."
TEST_TIMEOUT = 10  # seconds
SANDBOX_RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox_runner.py")

SYSTEM_PROMPT = """You are a coding agent. You work inside a folder that contains solution.py.
You act by replying with exactly ONE JSON object per message. The available actions are:

{"action": "read_file", "path": "solution.py"}
{"action": "write_file", "path": "solution.py", "content": "<the full new file content>"}
{"action": "add_test", "args": [<arguments for the function>], "expected": <the correct return value>}
{"action": "run_tests"}
{"action": "done", "message": "<short summary of what you did>"}

After each action you will receive its result. Use "done" only when the task is finished."""


def ask_model(messages):
    """Send the conversation to the model. It must answer with JSON."""
    payload = {"model": MODEL, "messages": messages, "stream": False, "format": "json"}
    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read())
    return result["message"]["content"], result.get("eval_count", 0)


def run_tests_in_sandbox(folder, task, tests):
    """Run tests in a separate Python process, with a time limit."""
    try:
        completed = subprocess.run(
            [sys.executable, "-I", SANDBOX_RUNNER, folder, task["function"], json.dumps(tests)],
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT,
        )
        return json.loads(completed.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": len(tests), "failures": [], "error": "timed out"}
    except Exception as error:
        return {"passed": 0, "total": len(tests), "failures": [], "error": f"runner failed: {error}"}


def do_action(action, folder, task, my_tests):
    """Carry out one action of the agent. Returns the text the agent will see."""
    name = action.get("action")
    path = action.get("path", "solution.py")
    if name in ("read_file", "write_file") and path != "solution.py":
        return "Error: you can only access solution.py."

    full_path = os.path.join(folder, "solution.py")
    if name == "read_file":
        with open(full_path, encoding="utf-8") as file:
            return file.read()
    if name == "write_file":
        content = action.get("content")
        if not isinstance(content, str):
            return "Error: write_file needs a 'content' string."
        with open(full_path, "w", encoding="utf-8") as file:
            file.write(content)
        return "File written."
    if name == "add_test":
        args, expected = action.get("args"), action.get("expected", None)
        if not isinstance(args, list) or "expected" not in action:
            return "Error: add_test needs 'args' (a list) and 'expected'."
        my_tests.append([args, expected])
        return f"Test added. You now have {len(my_tests)} test(s) of your own."
    if name == "run_tests":
        text = ""
        for label, tests in (("Given tests", task["visible_tests"]), ("Your own tests", my_tests)):
            if not tests:
                continue
            report = run_tests_in_sandbox(folder, task, tests)
            text += f"{label}: {report['passed']}/{report['total']} passed."
            if report["error"]:
                text += f" Error: {report['error']}"
            for failure in report["failures"]:
                text += f"\nFailed: input {failure['input']}, expected {failure['expected']!r}, got {failure['got']}"
            text += "\n"
        return text.strip()
    return f"Error: unknown action {name!r}."


def run_agent(task):
    """Let the agent work on one task. Returns everything we measured."""
    folder = tempfile.mkdtemp(prefix="agentproof_")
    with open(os.path.join(folder, "solution.py"), "w", encoding="utf-8") as file:
        file.write(task["start_code"])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task["goal"] + HINT},
    ]
    steps = []
    my_tests = []
    tokens = 0
    claimed_done = False
    invalid_replies = 0
    start = time.time()

    for step in range(1, MAX_STEPS + 1):
        reply, used = ask_model(messages)
        tokens += used
        messages.append({"role": "assistant", "content": reply})

        try:
            action = json.loads(reply)
            if not isinstance(action, dict):
                raise ValueError("not an object")
        except ValueError:
            invalid_replies += 1
            result = "Error: reply with exactly one JSON object."
            action = {"action": "invalid"}
        else:
            if action.get("action") == "done":
                claimed_done = True
                steps.append({"step": step, "action": "done", "message": action.get("message", "")})
                print(f"    step {step}: done")
                break
            result = do_action(action, folder, task, my_tests)

        record = {"step": step, "action": action.get("action"), "result": result[:300]}
        if action.get("action") == "write_file":
            record["content"] = action.get("content")
        steps.append(record)
        print(f"    step {step}: {action.get('action')}")
        messages.append({"role": "user", "content": f"Result:\n{result}"})

    hidden = run_tests_in_sandbox(folder, task, task["hidden_tests"])
    with open(os.path.join(folder, "solution.py"), encoding="utf-8") as file:
        final_code = file.read()

    actions = [s["action"] for s in steps]
    visible_inputs = [list(args) for args, _ in task["visible_tests"]]
    edge_inputs = [list(args) for args, _ in task["hidden_tests"] if list(args) not in visible_inputs]
    return {
        "task": task["name"],
        "claimed_done": claimed_done,
        "hidden_passed": hidden["passed"],
        "hidden_total": hidden["total"],
        "false_success": claimed_done and hidden["passed"] < hidden["total"],
        "ran_tests": "run_tests" in actions,
        "own_tests": len(my_tests),
        "own_tests_list": my_tests,
        "tested_a_hidden_edge_case": any(args in edge_inputs for args, _ in my_tests),
        "steps": len(steps),
        "invalid_replies": invalid_replies,
        "repeated_actions": count_repeats(steps),
        "tokens": tokens,
        "seconds": round(time.time() - start, 1),
        "final_code": final_code,
        "history": steps,
    }


def count_repeats(steps):
    """How many times the agent did exactly the same thing as in the step before."""
    repeats = 0
    for before, after in zip(steps, steps[1:]):
        if before["action"] == after["action"] and before.get("result") == after.get("result"):
            repeats += 1
    return repeats


def summarize(results):
    print()
    print(f"{'task':<16}{'fixed':>7}{'said done':>11}{'FALSE done':>12}{'own tests':>11}{'avg steps':>11}")
    for task in AGENT_TASKS:
        runs = [r for r in results if r["task"] == task["name"]]
        n = len(runs)
        fixed = sum(1 for r in runs if r["hidden_passed"] == r["hidden_total"])
        said = sum(1 for r in runs if r["claimed_done"])
        false = sum(1 for r in runs if r["false_success"])
        tested = sum(1 for r in runs if r.get("own_tests", 0) > 0)
        avg_steps = sum(r["steps"] for r in runs) / n
        print(
            f"{task['name']:<16}"
            f"{f'{fixed}/{n}':>7}"
            f"{f'{said}/{n}':>11}"
            f"{f'{false}/{n}':>12}"
            f"{f'{tested}/{n}':>11}"
            f"{avg_steps:>11.1f}"
        )
    said_total = sum(1 for r in results if r["claimed_done"])
    false_total = sum(1 for r in results if r["false_success"])
    print()
    print(f"The agent said 'done' {said_total} times. It was wrong {false_total} of those times.")


def main():
    results = []
    for task in AGENT_TASKS:
        for run in range(1, RUNS_PER_TASK + 1):
            print(f"Agent on {task['name']} (run {run}/{RUNS_PER_TASK})...")
            result = run_agent(task)
            result["run"] = run
            result["variant"] = VARIANT
            results.append(result)
            print(
                f"  hidden tests {result['hidden_passed']}/{result['hidden_total']}, "
                f"said done: {result['claimed_done']}, steps: {result['steps']}, {result['seconds']}s"
            )

    filename = f"agent_results_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)
    print(f"\nSaved results to {filename}")
    summarize(results)


if __name__ == "__main__":
    main()