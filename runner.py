import json
import time
import urllib.request
from datetime import datetime

from tasks import TASKS

MODEL = "qwen2.5-coder:7b"
URL = "http://localhost:11434/api/chat"
INSTRUCTION = "Reply with code only."


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
    """Run the model's code and check it against the task's tests."""
    namespace = {}
    try:
        exec(code, namespace)
        function = namespace[task["function"]]
    except Exception as error:
        return 0, f"code did not run: {error}"

    passed = 0
    for args, expected in task["tests"]:
        try:
            if function(*args) == expected:
                passed += 1
        except Exception:
            pass
    return passed, ""


def main():
    results = []
    for task in TASKS:
        print(f"Running: {task['name']}...")
        prompt = f"{task['prompt']} {INSTRUCTION}"
        answer, seconds, tokens = ask_model(prompt)
        code = clean_code(answer)
        passed, error = run_tests(code, task)
        total = len(task["tests"])

        results.append({
            "task": task["name"],
            "passed": passed,
            "total": total,
            "seconds": round(seconds, 1),
            "tokens": tokens,
            "followed_format": "```" not in answer,
            "error": error,
            "answer": answer,
        })
        print(f"  {passed}/{total} tests passed, {seconds:.1f}s, {tokens} tokens")

    filename = f"results_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    print()
    print(f"Saved results to {filename}")
    fully_solved = sum(1 for r in results if r["passed"] == r["total"])
    print(f"Fully solved: {fully_solved}/{len(results)} tasks")


if __name__ == "__main__":
    main()