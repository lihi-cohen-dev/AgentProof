import json
import time
import urllib.request

MODEL = "qwen2.5-coder:7b"
URL = "http://localhost:11434/api/chat"

task = "Write a Python function called add(a, b) that returns the sum of a and b. Reply with code only."

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": task}],
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

print(result["message"]["content"])
print("-" * 40)
print(f"Time: {elapsed:.1f} seconds")
print(f"Tokens generated: {result['eval_count']}")
# --- Check the answer ---
answer = result["message"]["content"]

followed_format = "```" not in answer
code = answer.replace("```python", "").replace("```", "").strip()

tests = [(2, 3, 5), (-1, 1, 0), (0, 0, 0), (2.5, 2.5, 5.0)]
namespace = {}
try:
    exec(code, namespace)
    add = namespace["add"]
    passed = sum(1 for a, b, expected in tests if add(a, b) == expected)
except Exception as error:
    print(f"Code failed to run: {error}")
    passed = 0

print(f"Tests passed: {passed}/{len(tests)}")
print(f"Followed 'code only' instruction: {followed_format}")