"""Runs test cases against solution.py. Started as a separate Python process.

Usage: python sandbox_worker.py <folder> <function name> <tests as JSON>
Prints one JSON line: {"passed": ..., "total": ..., "failures": [...], "error": ...}

This file uses only the standard library and imports nothing from AgentProof,
so the agent's code runs in a process that knows nothing about the benchmark.
"""
import contextlib
import io
import json
import sys


def main() -> None:
    folder, function_name, tests_json = sys.argv[1], sys.argv[2], sys.argv[3]
    tests = json.loads(tests_json)
    sys.path.insert(0, folder)

    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            import solution  # noqa: E402  (the agent's file)
        function = getattr(solution, function_name)
    except BaseException as error:  # the agent's code may raise anything, even SystemExit
        print(json.dumps({"passed": 0, "total": len(tests), "failures": [],
                          "error": f"could not load solution.py: {type(error).__name__}: {error}"}))
        return

    passed = 0
    failures = []
    for args, expected in tests:
        try:
            with contextlib.redirect_stdout(printed):
                got = function(*args)
        except BaseException as error:
            got = f"raised {type(error).__name__}: {error}"
        if got == expected:
            passed += 1
        else:
            failures.append({"input": args, "expected": expected, "got": repr(got)})

    print(json.dumps({"passed": passed, "total": len(tests), "failures": failures, "error": ""}))


if __name__ == "__main__":
    main()
