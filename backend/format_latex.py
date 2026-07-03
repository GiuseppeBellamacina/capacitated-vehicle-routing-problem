"""Format experimental results as LaTeX tables.

Usage:
    python format_latex.py --table --results ../results/config_small/results.json
    python format_latex.py --comparison
    python format_latex.py --comparison --output results/table_comparison.txt
"""

import argparse
import json
from pathlib import Path

from cvrp.instance import discover_instances
from cvrp.utils import discover_config_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LaTeX table formatter for CVRP results"
    )
    sub = parser.add_subparsers(dest="command", help="Output mode")

    # --table subcommand
    table_parser = sub.add_parser("table", help="Single-config results table")
    table_parser.add_argument(
        "--results",
        default="../results/results.json",
        help="Path to results.json (default: ../results/results.json)",
    )

    # --comparison subcommand
    comp_parser = sub.add_parser("comparison", help="Cross-config comparison table")
    comp_parser.add_argument(
        "--output",
        default="",
        help="Save to file instead of stdout (default: print to stdout)",
    )

    return parser.parse_args()


# ────────────────────────────────────────────────────────────────────────────
# TABLE mode
# ────────────────────────────────────────────────────────────────────────────


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


# ────────────────────────────────────────────────────────────────────────────
# COMPARISON mode
# ────────────────────────────────────────────────────────────────────────────


def _short_label(config_name: str) -> str:
    """Return a short display label for a config variant."""
    labels = {
        "config_small": "Small",
        "config_medium": "Medium",
        "config_large": "Large",
        "config_ultra": "Ultra",
        "config_explore": "Explore",
        "config_tuned": "Tuned",
    }
    return labels.get(config_name, config_name)


def format_comparison_table(output_file: Path | None = None):
    config_results = discover_config_results()
    if len(config_results) < 2:
        print(
            f"Info: Need at least 2 config result sets "
            f"(found {len(config_results)}). Nothing to compare."
        )
        return

    config_names = sorted(config_results.keys())
    instances_order = discover_instances()

    # Find common instances present in ALL configs
    common = None
    for cfg_name in config_names:
        insts = set(config_results[cfg_name].keys())
        common = insts if common is None else common & insts
    if not common:
        print("Warning: No instances in common across configs.")
        return

    instances = [n for n in instances_order if n in common]

    # ── Build LaTeX table ─────────────────────────────────────────────────
    n_cfg = len(config_names)
    col_spec = "l" + "c" * (1 + n_cfg)  # Instance + Optimal + N configs

    lines: list[str] = []
    lines.append("% Auto-generated cross-config comparison table")
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"  \centering")
    lines.append(
        r"  \caption{Config variant comparison — best solution cost and gap from BKS}"
    )
    lines.append(r"  \label{tab:config-comparison}")
    lines.append(f"  \\begin{{tabular}}{{{{{col_spec}}}}}")
    lines.append(r"    \toprule")

    # Header row
    header_cols = ["Instance", "Optimal"]
    for cfg_name in config_names:
        header_cols.append(_short_label(cfg_name))
    lines.append("    " + " & ".join(header_cols) + r" \\")
    lines.append(r"    \midrule")

    # Data rows
    for inst_name in instances:
        first = config_results[config_names[0]][inst_name]
        optimal = first["optimal"]
        opt_str = f"{optimal:,}" if optimal is not None else "--"

        row_cells = [inst_name, opt_str]
        for cfg_name in config_names:
            r = config_results[cfg_name][inst_name]
            best = r["best"]
            if optimal:
                gap = ((best - optimal) / optimal) * 100
                cell = f"{best:,.2f} ({gap:+.2f}\\%)"
            else:
                cell = f"{best:,.2f}"
            row_cells.append(cell)

        lines.append("    " + " & ".join(row_cells) + r" \\")

    # Footer
    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")

    # Legend row with actual config parameters
    legend_parts = []
    for cfg_name in config_names:
        label = _short_label(cfg_name)
        # Try to read params from the YAML config file
        cfg_file = Path("../config") / f"{cfg_name}.yaml"
        params = {}
        if cfg_file.exists():
            import yaml
            with open(cfg_file) as f:
                params = yaml.safe_load(f)
        pop = params.get("population_size", "?")
        tourn = params.get("tournament_size", "?")
        elite = params.get("elite_count", "?")
        gran = params.get("granular_size", "?")
        legend_parts.append(f"{label}: pop={pop}, tournament={tourn}, elite={elite}, granular={gran}")
    lines.append(r"  \vspace{4pt}")
    lines.append(r"  \caption*{\footnotesize " + "; ".join(legend_parts) + r"}")

    lines.append(r"\end{table}")

    output = "\n".join(lines) + "\n"

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output, encoding="utf-8")
        print(f"Comparison table saved to: {output_file}")
    else:
        print("\n" + "=" * 100)
        print("LATEX COMPARISON TABLE (Copy and paste into report.tex):")
        print("=" * 100)
        print(output)
        print("=" * 100)


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()

    if args.command == "table":
        format_table(Path(args.results))
    elif args.command == "comparison":
        out_path = Path(args.output) if args.output else None
        format_comparison_table(out_path)
    else:
        print("Error: you must specify a subcommand.")
        print("Example:  python format_latex.py table --results ../results/results.json")
        print("Example:  python format_latex.py comparison")
