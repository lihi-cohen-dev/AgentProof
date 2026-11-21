import glob
import json

latest = sorted(glob.glob("results_*.json"))[-1]
with open(latest, encoding="utf-8") as file:
    results = json.load(file)

print(f"File: {latest}\n")
for r in results:
    if r["passed"] < r["total"]:
        print(f"=== {r['task']} (run {r.get('run', 1)}): {r['passed']}/{r['total']} ===")
        if r["error"]:
            print(f"Error: {r['error']}")
        print(r["answer"])
        print()