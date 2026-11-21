"""Runs tests on the agent's code in a separate process.

Usage: python sandbox_runner.py <folder> <function name> <tests as JSON>
Prints one JSON line: {"passed": ..., "total": ..., "failures": [...], "error": ...}
"""
import contextlib
import io
import json
import sys


def main():
    folder, function_name, tests_json = sys.argv[1], sys.argv[2], sys.argv[3]
    tests = json.loads(tests_json)
    sys.path.insert(0, folder)

    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            import solution
        function = getattr(solution, function_name)
    except Exception as error:
        report = {"passed": 0, "total": len(tests), "failures": [], "error": f"could not load solution.py: {error}"}
        print(json.dumps(report))
        return

    passed = 0
    failures = []
    for args, expected in tests:
        try:
            with contextlib.redirect_stdout(printed):
                got = function(*args)
        except Exception as error:
            got = f"raised {type(error).__name__}: {error}"
        if got == expected:
            passed += 1
        else:
            failures.append({"input": args, "expected": expected, "got": repr(got)})

    report = {"passed": passed, "total": len(tests), "failures": failures, "error": ""}
    print(json.dumps(report))


if __name__ == "__main__":
    main()