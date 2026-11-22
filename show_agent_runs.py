import glob
import json
import sys

latest = sorted(glob.glob("agent_results_*.json"))[-1]
with open(latest, encoding="utf-8") as file:
    results = json.load(file)

only_task = sys.argv[1] if len(sys.argv) > 1 else None
print(f"File: {latest}\n")

for r in results:
    if only_task and r["task"] != only_task:
        continue

    fixed = r["hidden_passed"] == r["hidden_total"]
    if r["false_success"]:
        verdict = "FALSE SUCCESS - said done, but hidden tests fail"
    elif fixed and r["claimed_done"]:
        verdict = "FIXED and said done"
    elif fixed:
        verdict = "FIXED, but never said done"
    else:
        verdict = "NOT FIXED - ran out of steps"

    print("=" * 60)
    print(f"{r['task']} (run {r['run']}): {verdict}")
    print(f"Hidden tests: {r['hidden_passed']}/{r['hidden_total']}, steps: {r['steps']}, "
          f"time: {r['seconds']}s, tokens: {r['tokens']}")

    own = r.get("own_tests_list")
    if own is not None:
        print(f"Tests the agent wrote for itself: {len(own)}")
        for args, expected in own:
            print(f"   {r['task'].replace('fix_', '')}{tuple(args)} should return {expected!r}")
        print(f"Did one of them check a hidden edge case? {'YES' if r.get('tested_a_hidden_edge_case') else 'no'}")
    print("=" * 60)

    for s in r["history"]:
        print(f"\n--- step {s['step']}: {s['action']} ---")
        if s["action"] == "write_file":
            print(s.get("content", "(code was not saved in this results file)"))
        elif s["action"] == "done":
            print(f"Agent says: {s.get('message', '')}")
        else:
            print(s.get("result", ""))
    print()