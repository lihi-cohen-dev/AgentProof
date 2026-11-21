import contextlib
import io
import json
import time
import urllib.request
from datetime import datetime

from tasks import TASKS

MODEL = "qwen2.5-coder:7b"
URL = "http://localhost:11434/api/chat"
INSTRUCTION = "Reply with code only."
RUNS_PER_TASK = 3


def ask_model(prompt):
    """Send a prompt to the model. Return the answer, the time it took and the token count."""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    start = time.time()
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read())
    elapsed = time.time() - start
    return result["message"]["content"], elapsed, result["eval_count"]


def clean_code(answer):
    """Remove markdown fences the model may have added."""
    lines = answer.strip().splitlines()
    lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(lines)


def run_tests(code, task):
    """Run the model's code against the task's tests.
    Returns: tests passed, error message, and anything the code printed."""
    namespace = {}
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            exec(code, namespace)
        function = namespace[task["function"]]
    except Exception as error:
        return 0, f"code did not run: {error}", printed.getvalue()

    passed = 0
    for args, expected in task["tests"]:
        try:
            with contextlib.redirect_stdout(printed):
                if function(*args) == expected:
                    passed += 1
        except Exception:
            pass
    return passed, "", printed.getvalue()


def summarize(results):
    """Print one line per task with how often it was solved and the averages."""
    print()
    print(f"{'task':<16}{'solved':>8}{'format':>8}{'printed':>9}{'avg s':>8}{'avg tok':>9}")
    for task in TASKS:
        runs = [r for r in results if r["task"] == task["name"]]
        n = len(runs)
        solved = sum(1 for r in runs if r["passed"] == r["total"])
        formatted = sum(1 for r in runs if r["followed_format"])
        printed = sum(1 for r in runs if r["printed"])
        avg_seconds = sum(r["seconds"] for r in runs) / n
        avg_tokens = sum(r["tokens"] for r in runs) / n
        print(
            f"{task['name']:<16}"
            f"{f'{solved}/{n}':>8}"
            f"{f'{formatted}/{n}':>8}"
            f"{f'{printed}/{n}':>9}"
            f"{avg_seconds:>8.1f}"
            f"{avg_tokens:>9.0f}"
        )
    all_solved = sum(1 for r in results if r["passed"] == r["total"])
    print()
    print(f"Overall: {all_solved}/{len(results)} runs fully solved")


def main():
    results = []
    for task in TASKS:
        for run in range(1, RUNS_PER_TASK + 1):
            print(f"Running: {task['name']} (run {run}/{RUNS_PER_TASK})...")
            prompt = f"{task['prompt']} {INSTRUCTION}"
            answer, seconds, tokens = ask_model(prompt)
            code = clean_code(answer)
            passed, error, printed = run_tests(code, task)
            total = len(task["tests"])

            results.append({
                "task": task["name"],
                "run": run,
                "passed": passed,
                "total": total,
                "seconds": round(seconds, 1),
                "tokens": tokens,
                "followed_format": "```" not in answer,
                "printed": printed,
                "error": error,
                "answer": answer,
            })
            print(f"  {passed}/{total} tests passed, {seconds:.1f}s, {tokens} tokens")

    filename = f"results_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)
    print()
    print(f"Saved results to {filename}")

    summarize(results)


if __name__ == "__main__":
    main()