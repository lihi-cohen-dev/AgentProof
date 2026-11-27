# AgentProof

[![tests](https://github.com/lihi-cohen-dev/AgentProof/actions/workflows/tests.yml/badge.svg)](https://github.com/lihi-cohen-dev/AgentProof/actions/workflows/tests.yml)

**How far can you trust an AI coding agent when it says "done"?**

AgentProof gives a local AI model a buggy file and tools to fix it, lets it work on its own, and then checks its work with hidden tests it never saw. The main metric is **false success**: how often the agent says it is finished while the code is still broken.

## Key features

- **Agent benchmark:** a step-by-step agent loop with tools (`read_file`, `write_file`, `run_tests`, `done`, and `add_test` in one experiment).
- **Hidden tests:** the agent sees 2 tests; 5 to 6 hidden tests with edge cases decide whether the fix is real.
- **False-success metric**, plus fixes, steps, tokens, invalid replies and repeated actions.
- **Experiments as configuration:** `no_hint`, `edge_cases` (a prompt hint) and `self_tests` (the agent writes its own tests).
- **Isolated execution:** model-written code runs in a separate process with a time limit.
- **Swappable components:** model backend (Ollama or a scripted fake) and result storage (JSON files or SQLite).
- **Replay:** every step, including the code the agent wrote, can be replayed later.
- **54 automated tests** that run without a real model, on Linux and Windows in CI.

## Technologies

Python 3.11+ (standard library only for the benchmark) · Ollama · SQLite · pytest · GitHub Actions · matplotlib (chart only)

## Installation

```bash
git clone https://github.com/lihi-cohen-dev/AgentProof.git
cd AgentProof
pip install -r requirements-dev.txt     # pytest and matplotlib
```

To run against a real model, install [Ollama](https://ollama.com) and pull the model:

```bash
ollama pull qwen2.5-coder:7b
```

## Running

```bash
python -m agentproof                                  # 3 tasks x 5 runs, no hint, results to JSON
python -m agentproof --variant self_tests --runs 3    # another experiment
python -m agentproof --store sqlite                   # save to agentproof.db instead of JSON
python -m agentproof --tasks fix_decode --runs 1      # one task only
python -m agentproof --model scripted --runs 1        # demo with a fake agent, no model needed

python -m agentproof.replay fix_split_bill            # replay every step of the newest run
python scripts/make_chart.py                          # chart of the newest result of each experiment
python single_answer/runner.py                        # the earlier single-answer benchmark
```

Run `python -m agentproof --help` for all options.

## Tests

```bash
python -m pytest
```

The tests never call a real model. They use `ScriptedClient`, a fake model that replays prepared actions, so they are fast and deterministic. They cover:

| Test file | What it checks |
|---|---|
| `test_tasks.py` | Every buggy start file fails the hidden tests, and a correct reference solution passes them (the task data itself is right) |
| `test_sandbox.py` | Correct and wrong code, syntax errors, exceptions, `print`, `sys.exit` and infinite loops are all handled |
| `test_tools.py` | Tools refuse any path except `solution.py`, validate input, and never leak hidden tests |
| `test_agent.py` | Careful agent, "lazy" agent (false success), stuck agent (step limit), invalid JSON, unknown actions, prompt variants |
| `test_storage_and_metrics.py` | JSON and SQLite stores save the same data; summary counts are correct |
| `test_cli_and_llm.py` | Full command-line run, replay, and a clear error when Ollama is not running |

## Architecture

```mermaid
flowchart TB
    CLI["cli.py<br/>composition root"] --> B[Benchmark]
    CLI -.->|builds| LLM
    CLI -.->|builds| R
    CLI -.->|builds| S
    B --> A[Agent loop]
    B --> S["ResultStore (interface)"]
    A --> LLM["LLMClient (interface)"]
    A --> T["Tool (interface)"]
    T --> R["TestRunner (interface)"]
    LLM --- O[OllamaClient]
    LLM --- F[ScriptedClient]
    T --- T1[ReadFile]
    T --- T2[WriteFile]
    T --- T3[RunTests]
    T --- T4[AddTest]
    R --- P[SubprocessTestRunner]
    P --> W["sandbox_worker.py<br/>separate process"]
    S --- J[JsonResultStore]
    S --- Q[SqliteResultStore]
    B --> M["metrics.py<br/>summary table"]
```

### Project structure

```
agentproof/
  domain.py          Data objects: AgentTask, TestCase, TestReport, Step, RunResult
  tasks.py           The bug-fixing tasks (data only)
  llm/
    base.py          LLMClient interface and LLMError
    ollama.py        OllamaClient: talks to a local Ollama server
    scripted.py      ScriptedClient: fake model for tests and demos
  tools.py           Workspace and the agent's tools (one class per action)
  sandbox.py         TestRunner interface and SubprocessTestRunner
  sandbox_worker.py  Runs tests on the agent's code in a separate process
  prompts.py         System prompt and experiment variants
  agent.py           The agent loop
  benchmark.py       Runs tasks several times and saves results
  storage.py         ResultStore interface, JSON and SQLite implementations
  metrics.py         Summary numbers and table (pure functions)
  cli.py             Command line; the only place that picks concrete classes
  replay.py          Replays saved runs step by step
tests/               Automated tests (pytest)
scripts/make_chart.py
single_answer/       The earlier single-answer benchmark (9 tasks)
.github/workflows/   CI: tests on Ubuntu and Windows
```

### Architectural decisions

**Separation of responsibilities.** The first version was one script that did everything: talked to the model, ran the loop, executed tests, counted results and printed them. Each of these is now its own module with one job. The agent loop (`agent.py`) only decides what happens next; it does not know how tests run, where results go, or which model answers.

**Depending on interfaces (dependency inversion).** The core depends on four small interfaces: `LLMClient`, `Tool`, `TestRunner` and `ResultStore`. Concrete classes are chosen in one place, `cli.py`, and passed in. This is what makes the code testable: the tests pass a `ScriptedClient` instead of Ollama and run the real loop without a model.

**Replacing components without touching the logic.**
- *Model:* to use another provider, write one class that implements `LLMClient.chat()`. Nothing else changes.
- *Storage:* `--store json` or `--store sqlite`. Both implement `ResultStore.save()`; the benchmark does not know which one it uses. A PostgreSQL store would be one more class.
- *Execution:* `SubprocessTestRunner` gives process isolation and a time limit. A container-based runner (Docker) can replace it behind the same `TestRunner` interface, for real security isolation.

**Extending without modifying (open/closed).** A new agent action is a new `Tool` subclass. A new experiment is a new entry in `VARIANTS`. A new task is a new `AgentTask` in `tasks.py`. The agent loop stays the same.

**Error handling.** Failures in the agent's code (syntax errors, exceptions, `sys.exit`, infinite loops, stray `print`) are reported as test results, never as crashes. Invalid model replies are counted and the agent gets another chance. If Ollama is not running, the program prints a clear message and exits with an error code instead of a stack trace, and nothing half-finished is saved.

**Result format.** `RunResult.to_dict()` keeps the same fields as the first version, so older result files, the chart script and the replay tool all keep working.

## Results

Model: `qwen2.5-coder:7b`, running locally on a laptop CPU through Ollama. 3 bug-fixing tasks, 5 runs each, max 10 steps per run.

**Without any hint, the agent said "done" 11 times, and was wrong in 7 of them.**

| Task | Actually fixed | Said "done" | False success | Ran tests | Avg steps |
|---|---|---|---|---|---|
| fix_split_bill | 0/5 | 5/5 | **5/5** | 5/5 | 4.0 |
| fix_decode | 0/5 | 1/5 | 1/5 | 5/5 | 9.6 |
| fix_next_bus | 4/5 | 5/5 | 1/5 | 4/5 | 5.0 |

![False success and fixes in all three experiments](agent_results_chart.png)

### What the runs showed

**1. "The tests pass" is not "the code is correct".** In `fix_split_bill` the agent ran the tests in every run, saw them pass, and declared success in all 5 runs: *"The bug in the split_bill function has been fixed and all tests passed."* The hidden edge cases (splitting 0 cents, an amount smaller than the number of people) still failed.

**2. Two opposite ways to fail.** In `fix_split_bill` the agent was overconfident and stopped after about 4 steps. In `fix_decode` it was stuck, using almost all 10 steps without getting the fix right. A single "0/5 fixed" hides this difference; the step-by-step history shows it.

**3. A prompt hint did not help.** Adding *"think about edge cases that the visible tests may not cover"* changed how often the agent said "done" (8 instead of 11), not how often it was wrong when it did (5 of 8, 63%, against 7 of 11, 64%).

**4. Self-written tests did not help either.** With an `add_test` tool the agent wrote tests in all 15 runs, but they were wrong:

| Task | A test the agent wrote | The problem |
|---|---|---|
| fix_split_bill | `split_bill(10, 3)` should return `[3, 3, 4]` | Opposite order to the given test `[3, 3, 2, 2]` |
| fix_decode | `decode("a1b2c3")` should return `"abbcddd"` | Wrong answer (correct: `"abbccc"`) |
| fix_next_bus | `next_bus("18:00", "16:00")` | Wrong input type: one time instead of a list |

None of its tests checked a hidden edge case. It spent its steps "fixing" correct code to satisfy its own wrong tests and ran out of steps in 14 of 15 runs. False success dropped to 1, but only because it almost never finished. **An agent that misunderstands the task writes tests that share the misunderstanding.**

### Earlier single-answer benchmark

Before agent mode, the same model answered 9 coding tasks directly, 3 times each (`single_answer/`). It solved 23 of 27 runs, but ignored the instruction "Reply with code only" in all 27, and its code printed unrequested output in 4 runs. The bugs used in the agent tasks are the mistakes it made there.

## Limits

These results come from one small model, 3 agent tasks and 15 runs per experiment. They show that false success happens and what it looks like, not how often it happens for AI agents in general.

## Roadmap

- [x] Agent mode with tools, visible and hidden tests, false-success metric
- [x] Three experiments: no hint, edge-case hint, self-written tests
- [x] Modular architecture, swappable model and storage, automated tests and CI
- [ ] More tasks and more runs, for stronger statistics
- [ ] Compare several models (one new `LLMClient` per provider)
- [ ] Container-based `TestRunner` for real security isolation
- [ ] More steps per run, to see if self-testing helps when the agent is not short of steps
