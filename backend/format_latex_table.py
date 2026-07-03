"""Format experimental results as LaTeX table rows.

Usage:
    python format_latex_table.py --results ../results/config_small/results.json
"""

import argparse
import json
from pathlib import Path

from cvrp.instance import discover_instances


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LaTeX table formatter for CVRP results"
    )
    parser.add_argument(
        "--results",
        default="../results/results.json",
        help="Path to results.json (default: ../results/results.json)",
    )
    return parser.parse_args()


def format_table(results_file: Path):
    if not results_file.exists():
        print(f"Error: {results_file} not found.")
        return

    with open(results_file) as f:
        results = json.load(f)

    instances_order = discover_instances()

    print("\n" + "=" * 80)
    print("LATEX TABLE ROWS (Copy and paste into report.tex):")
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

        if optimal:
            gap = ((best - optimal) / optimal) * 100
            gap_str = f"{gap:.2f}\\%"
        else:
            gap_str = "-"

        vehicles_used = len(r.get("routes", []))
        opt_str = f"{optimal:,}" if optimal is not None else "-"

        row = (
            f"{name:<12} & {best:>8.2f} & {mean:>8.2f} & {std_dev:>8.2f} "
            f"& {opt_str:>7} & {gap_str:>7} & {vehicles_used:>7} \\\\"
        )
        print(row)

    print("=" * 80)


if __name__ == "__main__":
    args = parse_args()
    format_table(Path(args.results))
