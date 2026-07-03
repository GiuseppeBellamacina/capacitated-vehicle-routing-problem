"""Script to format experimental results from results.json as LaTeX table rows."""

import json
from pathlib import Path

RESULTS_FILE = Path(__file__).parent.parent / "results" / "results.json"


def format_table():
    if not RESULTS_FILE.exists():
        print(f"Error: {RESULTS_FILE} not found. Please run run_experiments.py first.")
        return

    with open(RESULTS_FILE) as f:
        results = json.load(f)

    instances_order = [
        "A-n45-k7",
        "A-n60-k9",
        "A-n80-k10",
        "B-n56-k7",
        "B-n66-k9",
        "B-n78-k10",
        "E-n76-k8",
        "E-n101-k14",
        "P-n50-k10",
        "P-n101-k4",
    ]

    print("\n" + "=" * 80)
    print("LATEX TABLE ROWS (Copy and paste into Table 3 in report.tex):")
    print("=" * 80)

    for name in instances_order:
        if name not in results:
            print(f"{name:<12} & TBD & TBD & TBD & Optimal & TBD & Vehicles \\\\")
            continue

        r = results[name]
        best = r["best"]
        mean = r["mean"]
        std_dev = r["std_dev"]
        optimal = r["optimal"]

        # Calculate gap
        if optimal:
            gap = ((best - optimal) / optimal) * 100
            gap_str = f"{gap:.2f}\\%"
        else:
            gap_str = "-"

        # Get number of vehicles used in the best solution
        # (the length of routes list in results)
        vehicles_used = len(r.get("routes", []))

        # In case the optimal is none, format it nicely
        opt_str = f"{optimal:,}" if optimal is not None else "-"

        row = f"{name:<12} & {best:>8.2f} & {mean:>8.2f} & {std_dev:>8.2f} & {opt_str:>7} & {gap_str:>7} & {vehicles_used:>7} \\\\"
        print(row)

    print("=" * 80)


if __name__ == "__main__":
    format_table()
