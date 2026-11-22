import glob
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TASKS = ["fix_split_bill", "fix_decode", "fix_next_bus"]
COLORS = {"no_hint": "#2a78d6", "edge_cases": "#eb6834", "self_tests": "#1baf7a"}
NAMES = {"no_hint": "No hint", "edge_cases": "\"Think about edge cases\" hint", "self_tests": "Agent writes its own tests"}


def latest_file_per_variant():
    """For each variant, keep the newest agent_results file."""
    latest = {}
    for path in sorted(glob.glob("agent_results_*.json")):
        with open(path, encoding="utf-8") as file:
            results = json.load(file)
        if not results:
            continue
        variant = results[0].get("variant", "no_hint")
        latest[variant] = (path, results)
    return latest


def count(results, task, key):
    runs = [r for r in results if r["task"] == task]
    if key == "fixed":
        return sum(1 for r in runs if r["hidden_passed"] == r["hidden_total"]), len(runs)
    return sum(1 for r in runs if r["false_success"]), len(runs)


def main():
    data = latest_file_per_variant()
    variants = [v for v in ("no_hint", "edge_cases", "self_tests") if v in data]
    for v in variants:
        print(f"{NAMES[v]}: {data[v][0]}")

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    panels = [("false", "Said \"done\" but the code was broken"), ("fixed", "Actually fixed (hidden tests pass)")]
    width = 0.26
    runs_per_task = 5

    for ax, (key, title) in zip(axes, panels):
        for i, v in enumerate(variants):
            results = data[v][1]
            values = []
            for task in TASKS:
                value, runs_per_task = count(results, task, key)
                values.append(value)
            xs = [t + (i - (len(variants) - 1) / 2) * (width + 0.03) for t in range(len(TASKS))]
            bars = ax.bar(xs, values, width, color=COLORS[v], label=NAMES[v], zorder=3)
            for bar, value in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, value + 0.1, str(value),
                        ha="center", va="bottom", fontsize=10, color="#0b0b0b")
        ax.set_title(title, fontsize=12, color="#0b0b0b", loc="left", pad=10)
        ax.set_xticks(range(len(TASKS)))
        ax.set_xticklabels(TASKS, fontsize=10, color="#52514e")
        ax.set_ylim(0, runs_per_task + 0.8)
        ax.set_yticks(range(runs_per_task + 1))
        ax.tick_params(axis="y", colors="#52514e", length=0)
        ax.tick_params(axis="x", length=0)
        ax.grid(axis="y", color="#e5e4df", linewidth=0.8, zorder=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7")
    axes[0].set_ylabel(f"Runs (out of {runs_per_task})", color="#52514e", fontsize=10)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.055, 0.905), ncol=3, frameon=False, fontsize=10)
    fig.suptitle("Neither a hint nor self-written tests made the agent reliable",
                 x=0.06, y=0.985, ha="left", fontsize=14, fontweight="bold", color="#0b0b0b")
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axes:
        ax.set_facecolor("#fcfcfb")
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.08, top=0.74, wspace=0.08)
    fig.savefig("agent_results_chart.png", dpi=160, bbox_inches="tight", facecolor="#fcfcfb")
    print("Saved agent_results_chart.png")


if __name__ == "__main__":
    main()