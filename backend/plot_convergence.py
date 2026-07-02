"""Script to generate publication-quality plots for the CVRP HGA report.

Generates:
  - Convergence curves for 3 representative instances
  - Best-route 2D visualizations for 3 representative instances
  - Summary chart: best cost vs BKS across all instances, grouped by set
  - Gap chart: % gap from optimal for all instances
  - Box plot: per-run cost distribution showing algorithm stability
  - Runtime chart: execution time vs instance dimension
  - Radar chart: normalized performance comparison across sets A/B/E/P
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
import numpy as np
import yaml

# Allow importing from cvrp package
sys.path.insert(0, str(Path(__file__).parent))

from cvrp.instance import read_instance

RESULTS_FILE = Path(__file__).parent.parent / "results" / "results.json"
IMGS_DIR = Path(__file__).parent.parent / "docs" / "report" / "imgs"
INSTANCES_DIR = Path(__file__).parent.parent / "instances"

# Output subdirectories by chart type
CONV_DIR = IMGS_DIR / "convergence"
ROUTES_DIR = IMGS_DIR / "routes"
SUMMARY_DIR = IMGS_DIR / "summary"

# Load max evaluations from config.yaml dynamically
def load_max_evals() -> int:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
            return cfg.get("max_evaluations", 350000)
    return 350000

MAX_EVALS = load_max_evals()

# Select representative instances
REPRESENTATIVE_INSTANCES = [
    "A-n45-k7",
    "B-n66-k9",
    "E-n101-k14",
    "P-n50-k10",
    "P-n101-k4"
]

# Color palette for routes -- elegant, colorblind-friendly, publication-quality
# Based on the Tol Vibrant qualitative scheme
ROUTE_COLORS = [
    "#0077BB", "#EE7733", "#009988", "#EE3377", "#33BBEE",
    "#CC3311", "#BBBBBB", "#AA3377", "#228833", "#4477AA",
    "#DDCC77", "#66CCEE", "#885522", "#CCBB44", "#AA4466",
    "#77AADD", "#99DDBB", "#DDAA33", "#5533AA", "#BB6644",
]

# All benchmark instances (ordered by set)
ALL_INSTANCES = [
    "A-n45-k7", "A-n60-k9", "A-n80-k10",
    "B-n56-k7", "B-n66-k9", "B-n78-k10",
    "E-n76-k8", "E-n101-k14",
    "P-n50-k10", "P-n101-k4",
]

# Set-level colors for summary charts
SET_COLORS = {
    "A": "#0077BB",
    "B": "#EE7733",
    "E": "#009988",
    "P": "#CC3311",
}


def _set_publication_style():
    """Apply a clean, publication-quality matplotlib style."""
    plt.rcParams.update({
        # Typography
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "figure.titlesize": 11,
        # Layout
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.minor.size": 0,
        "ytick.minor.size": 0,
        "grid.alpha": 0.12,
        "grid.linestyle": "-",
        "grid.linewidth": 0.4,
        # Figure
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.08,
        # Legend
        "legend.frameon": True,
        "legend.framealpha": 0.92,
        "legend.edgecolor": "#cccccc",
        "legend.fancybox": False,
        "legend.borderpad": 0.4,
        "legend.borderaxespad": 0.5,
        # Misc
        "axes.axisbelow": True,
        "lines.linewidth": 1.2,
        "patch.linewidth": 0.6,
    })


# =============================================================================
#  Convergence & Route plots (representative instances)
# =============================================================================

def generate_convergence_plots(results: dict):
    """Generate publication-quality convergence curve plots."""
    _set_publication_style()

    for name in REPRESENTATIVE_INSTANCES:
        if name not in results:
            print(f"Warning: {name} results not found in results.json. Skipping.")
            continue

        res = results[name]
        convergence = res["convergence"]
        optimal = res["optimal"]
        best_cost = res["best"]

        fig, ax = plt.subplots(figsize=(6.0, 3.6))

        # Interpolate each run's history to a common grid of 100 points
        grid_points = 100
        x_vals = np.linspace(0, MAX_EVALS, grid_points)
        interpolated_runs = []

        for run_history in convergence:
            L = len(run_history)
            if L > 1:
                x_original = np.linspace(0, MAX_EVALS, L)
                y_interp = np.interp(x_vals, x_original, run_history)
                interpolated_runs.append(y_interp)
            else:
                interpolated_runs.append(np.full_like(x_vals, run_history[0]))

        conv_matrix = np.array(interpolated_runs)
        mean_history = np.mean(conv_matrix, axis=0)
        std_history = np.std(conv_matrix, axis=0)
        min_history = np.min(conv_matrix, axis=0)

        # 1. Individual runs -- subtle gray
        for run_idx in range(conv_matrix.shape[0]):
            ax.plot(x_vals, conv_matrix[run_idx], color="#cccccc", alpha=0.35,
                    linewidth=0.6, label="Individual runs" if run_idx == 0 else "")

        # 2. Standard deviation band
        ax.fill_between(x_vals, mean_history - std_history, mean_history + std_history,
                        color="#0077BB", alpha=0.10, label="+/-1 s.d.")

        # 3. Mean history
        ax.plot(x_vals, mean_history, color="#0077BB", linewidth=1.6, label="Mean")

        # 4. Best envelope
        ax.plot(x_vals, min_history, color="#009988", linestyle="--", linewidth=1.2,
                label="Best")

        # 5. Optimal reference line
        if optimal:
            ax.axhline(y=optimal, color="#CC3311", linestyle=":", linewidth=1.2,
                       label=f"BKS ({optimal})")

        # Title
        gap_str = ""
        if optimal:
            gap = ((best_cost - optimal) / optimal) * 100
            gap_str = f" (gap {gap:+.2f}%)"
        ax.set_title(
            f"{name}  --  Convergence  |  "
            f"Best: {best_cost:.0f}{gap_str}  |  "
            f"Runs: {conv_matrix.shape[0]}",
            fontsize=9.5, fontweight="normal", loc="center", pad=10,
        )

        ax.set_xlabel("Fitness evaluations (FE)")
        ax.set_ylabel("Cost")
        ax.grid(True)
        ax.legend(loc="upper right", framealpha=0.85, borderpad=0.4,
                  handlelength=1.6, handletextpad=0.5)
        ax.ticklabel_format(axis="x", style="scientific", scilimits=(3, 4))

        fig.tight_layout(pad=0.5)
        output_path = CONV_DIR / f"convergence_{name}.png"
        fig.savefig(output_path, facecolor="white", edgecolor="none")
        plt.close(fig)
        print(f"Generated convergence plot: {output_path}")


def generate_route_plots(results: dict):
    """Generate publication-quality best-route visualization on 2D maps."""
    _set_publication_style()

    for name in REPRESENTATIVE_INSTANCES:
        if name not in results:
            print(f"Warning: {name} results not found in results.json. Skipping route plot.")
            continue

        instance_path = INSTANCES_DIR / f"{name}.vrp"
        if not instance_path.exists():
            print(f"Warning: Instance file {instance_path} not found. Skipping route plot.")
            continue

        res = results[name]
        routes = res.get("routes", [])
        if not routes:
            print(f"Warning: No routes found for {name}. Skipping route plot.")
            continue

        instance = read_instance(instance_path)
        coords = instance.node_coords
        depot_idx = instance.depot
        demands = instance.demands

        best_cost = res["best"]
        optimal = res.get("optimal")
        num_vehicles_used = len(routes)

        fig, ax = plt.subplots(figsize=(6.0, 6.0 * 0.75))

        # Axis limits with 6% padding
        depot_x, depot_y = coords[depot_idx]
        all_x = [c[0] for c in coords]
        all_y = [c[1] for c in coords]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        x_pad = (x_max - x_min) * 0.06 + 2
        y_pad = (y_max - y_min) * 0.06 + 2
        ax.set_xlim(x_min - x_pad, x_max + x_pad)
        ax.set_ylim(y_min - y_pad, y_max + y_pad)

        # Draw route edges (curved, with arrows)
        for ri, route in enumerate(routes):
            color = ROUTE_COLORS[ri % len(ROUTE_COLORS)]
            path_nodes = [depot_idx] + route + [depot_idx]
            n_seg = len(path_nodes) - 1

            for si in range(n_seg):
                x0, y0 = coords[path_nodes[si]]
                x1, y1 = coords[path_nodes[si + 1]]
                rad_sign = 1 if si % 2 == 0 else -1
                patch = FancyArrowPatch(
                    posA=(x0, y0), posB=(x1, y1),
                    arrowstyle="-|>", mutation_scale=6,
                    connectionstyle=f"arc3,rad={rad_sign * 0.10}",
                    color=color, linewidth=1.2, alpha=0.82, zorder=3,
                    joinstyle="round", capstyle="round",
                )
                ax.add_patch(patch)

        # Customer nodes (sized by demand)
        customer_nodes: list[int] = []
        for route in routes:
            for n in route:
                if n not in customer_nodes:
                    customer_nodes.append(n)

        cx_vals = [coords[n][0] for n in customer_nodes]
        cy_vals = [coords[n][1] for n in customer_nodes]
        demand_vals = np.array([demands[n] for n in customer_nodes], dtype=float)

        d_min, d_max = demand_vals.min(), demand_vals.max()
        if d_max > d_min:
            sizes = 18 + (demand_vals - d_min) / (d_max - d_min) * 102
        else:
            sizes = np.full_like(demand_vals, 35.0)

        ax.scatter(cx_vals, cy_vals, s=sizes, c="#444444", marker="o",
                   zorder=4, edgecolors="white", linewidths=0.5, alpha=0.88)

        # Depot
        ax.scatter([depot_x], [depot_y], c="#CC3311", marker="D", s=100,
                   zorder=6, edgecolors="#661100", linewidths=1.2)

        # Route labels
        for ri, route in enumerate(routes):
            if not route:
                continue
            color = ROUTE_COLORS[ri % len(ROUTE_COLORS)]
            first = route[0]
            mid_x = (depot_x + coords[first][0]) / 2
            mid_y = (depot_y + coords[first][1]) / 2
            dx_edge = coords[first][0] - depot_x
            dy_edge = coords[first][1] - depot_y
            norm = np.hypot(dx_edge, dy_edge) or 1.0
            offset_x = -dy_edge / norm * 6
            offset_y = dx_edge / norm * 6
            ax.annotate(
                f"{ri + 1}", (mid_x, mid_y),
                textcoords="offset points", xytext=(offset_x, offset_y),
                fontsize=6.5, fontweight="bold", color=color,
                ha="center", va="center",
                bbox=dict(boxstyle="circle,pad=0.15", facecolor="white",
                          edgecolor=color, linewidth=0.9, alpha=0.92),
                zorder=7,
            )

        # Demand legend
        if d_max > d_min:
            legend_demands = [d_min, (d_min + d_max) / 2, d_max]
            legend_sizes = [18 + (d - d_min) / (d_max - d_min) * 102 for d in legend_demands]
            legend_handles = []
            for d_val, s_val in zip(legend_demands, legend_sizes):
                legend_handles.append(Line2D(
                    [0], [0], marker="o", color="none",
                    markerfacecolor="#444444", markeredgecolor="white",
                    markeredgewidth=0.5, markersize=np.sqrt(s_val), alpha=0.88,
                    label=f"{int(d_val)}",
                ))
            leg1 = ax.legend(handles=legend_handles, loc="lower left",
                             title="Demand", title_fontsize=7,
                             framealpha=0.85, borderpad=0.5, handletextpad=0.6)
            ax.add_artist(leg1)

        # Depot legend
        depot_handle = Line2D([0], [0], marker="D", color="none",
                              markerfacecolor="#CC3311", markeredgecolor="#661100",
                              markeredgewidth=1.0, markersize=7.5)
        ax.legend(handles=[depot_handle], labels=["Depot"], loc="lower right",
                  framealpha=0.85, borderpad=0.5)

        # Title
        gap_str = ""
        if optimal:
            gap = ((best_cost - optimal) / optimal) * 100
            gap_str = f" (gap {gap:+.2f}%)"
        title_line1 = f"{name}  --  Best solution"
        title_line2 = (
            f"Cost: {best_cost:.0f}{gap_str}    "
            f"Vehicles: {num_vehicles_used}/{instance.num_vehicles}    "
            f"Customers: {len(customer_nodes)}"
        )
        ax.set_title(f"{title_line1}\n{title_line2}", fontsize=9.5,
                     fontweight="normal", loc="center", pad=10, linespacing=1.4)

        ax.set_xlabel("x-coordinate")
        ax.set_ylabel("y-coordinate")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.12, linewidth=0.4)

        output_path = ROUTES_DIR / f"routes_{name}.png"
        fig.savefig(output_path, facecolor="white", edgecolor="none")
        plt.close(fig)
        print(f"Generated route plot: {output_path}")


# =============================================================================
#  Summary charts (all instances)
# =============================================================================

def _get_available(results: dict) -> list[str]:
    """Return ALL_INSTANCES filtered to those present in results."""
    return [n for n in ALL_INSTANCES if n in results]


def generate_summary_chart(results: dict):
    """Grouped bar chart: best cost vs BKS for all instances, grouped by set."""
    _set_publication_style()

    available = _get_available(results)
    if not available:
        print("Warning: No results available for summary chart.")
        return

    # Build data (only instances with known BKS for the grouped comparison)
    labels = []
    best_vals = []
    opt_vals = []
    bar_colors = []
    for name in available:
        r = results[name]
        if not r["optimal"]:
            continue
        labels.append(name)
        best_vals.append(r["best"])
        opt_vals.append(r["optimal"])
        bar_colors.append(SET_COLORS[name[0]])

    if not labels:
        print("Warning: No instances with known BKS for summary chart.")
        return

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    x = np.arange(len(labels))
    width = 0.35

    ax.bar(x - width / 2, best_vals, width, color=bar_colors,
           edgecolor="white", linewidth=0.4, alpha=0.88, label="HGA best")
    ax.bar(x + width / 2, opt_vals, width,
           color="#dddddd", edgecolor="#aaaaaa", linewidth=0.4,
           hatch="///", alpha=0.7, label="BKS")

    # Annotate gap % above bars
    for i, name in enumerate(labels):
        r = results[name]
        if r["optimal"]:
            gap_pct = ((r["best"] - r["optimal"]) / r["optimal"]) * 100
            ax.annotate(f"{gap_pct:+.1f}%", (x[i], r["best"]),
                        textcoords="offset points", xytext=(0, 5),
                        fontsize=6, ha="center", color="#444444")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Cost")
    ax.set_title("Best solution cost vs best-known solution (BKS)", fontsize=9.5,
                 fontweight="normal", pad=10)
    ax.grid(True, axis="y")
    ax.legend(loc="upper left", framealpha=0.85, borderpad=0.4)

    fig.tight_layout(pad=0.6)
    output_path = SUMMARY_DIR / "summary_best_vs_bks.png"
    fig.savefig(output_path, facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"Generated summary chart: {output_path}")


def generate_gap_chart(results: dict):
    """Bar chart of % gap from optimal for all instances, colored by set."""
    _set_publication_style()

    available = _get_available(results)
    if not available:
        print("Warning: No results available for gap chart.")
        return

    labels = []
    gaps = []
    colors = []
    for name in available:
        r = results[name]
        if r["optimal"]:
            labels.append(name)
            gaps.append(((r["best"] - r["optimal"]) / r["optimal"]) * 100)
            colors.append(SET_COLORS[name[0]])

    if not labels:
        print("Warning: No instances with known optimal for gap chart.")
        return

    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    x = np.arange(len(labels))
    ax.bar(x, gaps, color=colors, edgecolor="white", linewidth=0.4, alpha=0.88)

    for i, g in enumerate(gaps):
        ax.annotate(f"{g:+.2f}%", (x[i], g),
                    textcoords="offset points",
                    xytext=(0, 4 if g >= 0 else -10),
                    fontsize=7, ha="center", color="#333333")

    ax.axhline(y=0, color="#999999", linewidth=0.6, linestyle="-")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Gap from BKS (%)")
    ax.set_title("Relative gap from best-known solution", fontsize=9.5,
                 fontweight="normal", pad=10)
    ax.grid(True, axis="y")

    fig.tight_layout(pad=0.6)
    output_path = SUMMARY_DIR / "summary_gap.png"
    fig.savefig(output_path, facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"Generated gap chart: {output_path}")


def generate_boxplot(results: dict):
    """Box plot of per-run costs across all instances showing HGA stability."""
    _set_publication_style()

    available = _get_available(results)
    if not available:
        print("Warning: No results available for boxplot.")
        return

    # Normalize each instance's per-run costs by its BKS for cross-instance comparability
    data = []
    labels = []
    colors = []
    for name in available:
        r = results[name]
        if not r["optimal"]:
            continue
        opt = r["optimal"]
        normalized = [(c / opt) * 100 for c in r["per_run_costs"]]
        data.append(normalized)
        labels.append(name)
        colors.append(SET_COLORS[name[0]])

    if not data:
        print("Warning: No instances with known BKS for boxplot.")
        return

    fig, ax = plt.subplots(figsize=(7.5, 3.8))

    bp = ax.boxplot(data, patch_artist=True, widths=0.6,
                    medianprops={"color": "#333333", "linewidth": 1.0},
                    whiskerprops={"linewidth": 0.7, "color": "#666666"},
                    capprops={"linewidth": 0.7, "color": "#666666"},
                    flierprops={"marker": "o", "markersize": 3,
                                "markerfacecolor": "#CC3311",
                                "markeredgecolor": "#CC3311", "alpha": 0.6})

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
        patch.set_edgecolor(color)
        patch.set_linewidth(0.8)

    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
    ax.axhline(y=100, color="#CC3311", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.set_ylabel("Cost (% of BKS)")
    ax.set_title("Per-run cost distribution across 5 independent runs (normalized by BKS)",
                 fontsize=9.5, fontweight="normal", pad=10)
    ax.grid(True, axis="y")

    fig.tight_layout(pad=0.6)
    output_path = SUMMARY_DIR / "summary_boxplot.png"
    fig.savefig(output_path, facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"Generated boxplot: {output_path}")


def generate_runtime_chart(results: dict):
    """Scatter plot: execution time vs instance dimension, colored by set."""
    _set_publication_style()

    available = _get_available(results)
    if not available:
        print("Warning: No results available for runtime chart.")
        return

    fig, ax = plt.subplots(figsize=(5.5, 3.3))

    for name in available:
        r = results[name]
        dim = r["dimension"]
        t = r["execution_time"]
        set_name = name[0]
        color = SET_COLORS[set_name]
        ax.scatter(dim, t, c=color, s=50, edgecolors="white", linewidths=0.5,
                   zorder=4, alpha=0.88)
        ax.annotate(name, (dim, t), textcoords="offset points",
                    xytext=(5, 4), fontsize=5.5, color="#555555",
                    ha="left", va="bottom")

    ax.set_xlabel("Instance dimension (nodes)")
    ax.set_ylabel("Execution time (s)")
    ax.set_title("Computational cost vs instance size", fontsize=9.5,
                 fontweight="normal", pad=10)
    ax.grid(True)

    legend_handles = [Line2D([0], [0], marker="o", color="none",
                              markerfacecolor=SET_COLORS[s],
                              markersize=6, label=f"Set {s}")
                      for s in ["A", "B", "E", "P"]]
    ax.legend(handles=legend_handles, loc="upper left", framealpha=0.85,
              borderpad=0.4, handletextpad=0.4)

    fig.tight_layout(pad=0.6)
    output_path = SUMMARY_DIR / "summary_runtime.png"
    fig.savefig(output_path, facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"Generated runtime chart: {output_path}")


def generate_radar_chart(results: dict):
    """Radar/spider chart comparing normalized performance across the 4 sets.

    Aggregates per-set averages and normalizes each metric to [0, 1]
    where 1.0 = best performance across all sets.
    """
    _set_publication_style()

    available = _get_available(results)
    if not available:
        print("Warning: No results available for radar chart.")
        return

    # Collect per-instance data, only instances with known BKS
    sets_data: dict[str, list[dict]] = {"A": [], "B": [], "E": [], "P": []}
    for name in available:
        r = results[name]
        if not r["optimal"]:
            continue
        set_name = name[0]
        sets_data[set_name].append(r)

    # Ensure at least one instance per set
    active_sets = [s for s in ["A", "B", "E", "P"] if sets_data[s]]
    if len(active_sets) < 2:
        print("Warning: Need at least 2 sets with data for radar chart.")
        return

    # Compute per-set aggregates
    set_metrics: dict[str, dict[str, float]] = {}
    print("\n  [Radar] Raw per-set metrics:")
    for s in active_sets:
        instances = sets_data[s]
        n = len(instances)
        avg_cv = sum(r["std_dev"] / r["mean"] for r in instances) / n
        avg_gap = sum(
            ((r["best"] - r["optimal"]) / r["optimal"]) * 100 for r in instances
        ) / n
        avg_time_per_node = sum(
            r["execution_time"] / r["dimension"] for r in instances
        ) / n
        total_gens = sum(sum(r["generations_to_best"]) for r in instances)
        total_runs = sum(len(r["generations_to_best"]) for r in instances)
        avg_gens = total_gens / total_runs if total_runs else 0
        # Avg route length: customers per vehicle (lower = more balanced / more specialized routes)
        avg_route_len = sum(
            sum(len(route) for route in r["routes"]) / (len(r["routes"]) or 1)
            for r in instances
        ) / n

        set_metrics[s] = {
            "Route length": avg_route_len,
            "Stability (CV)": avg_cv,
            "Gap %": avg_gap,
            "Time/node (s)": avg_time_per_node,
            "Convergence (gens)": avg_gens,
        }
        print(f"    Set {s}: rlen={avg_route_len:.1f}  cv={avg_cv:.4f}  "
              f"gap={avg_gap:.2f}%  t/node={avg_time_per_node:.2f}s  gens={avg_gens:.0f}")

    # Metric display names — all metrics: lower raw value = better performance
    metric_keys = list(next(iter(set_metrics.values())).keys())
    lower_is_better = [True, True, True, True, True]

    # Normalize: soft range [0.15, 1.0] — worst set never collapses to zero
    LO_FLOOR, HI_CEIL = 0.15, 1.0
    set_scores: dict[str, list[float]] = {s: [] for s in active_sets}
    print(f"\n  [Radar] Normalized scores (soft range [{LO_FLOOR}, {HI_CEIL}]):")
    for mi, key in enumerate(metric_keys):
        values = [set_metrics[s][key] for s in active_sets]
        vmin, vmax = min(values), max(values)
        if vmax == vmin:
            for s in active_sets:
                set_scores[s].append(LO_FLOOR + (HI_CEIL - LO_FLOOR) * 0.5)
        else:
            for s in active_sets:
                v = set_metrics[s][key]
                if lower_is_better[mi]:
                    raw = (vmax - v) / (vmax - vmin)
                else:
                    raw = (v - vmin) / (vmax - vmin)
                set_scores[s].append(LO_FLOOR + (HI_CEIL - LO_FLOOR) * raw)
        scores_str = "  ".join(
            f"{s}={set_scores[s][-1]:.2f}" for s in active_sets
        )
        print(f"    {key:<20s}  {scores_str}")

    # ---- Plot ----
    n_metrics = len(metric_keys)
    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]  # close the loop

    # Short labels for the polar chart
    short_labels = [k.replace(" (", "\n(") for k in metric_keys]

    fig, ax = plt.subplots(figsize=(5.5, 5.5), subplot_kw={"projection": "polar"})
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    for s in active_sets:
        values = set_scores[s] + set_scores[s][:1]
        color = SET_COLORS[s]
        ax.fill(angles, values, color=color, alpha=0.08)
        ax.plot(angles, values, color=color, linewidth=1.4, label=f"Set {s}",
                marker="o", markersize=4.5, markeredgecolor="white",
                markeredgewidth=0.5)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(short_labels, fontsize=7.5)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([LO_FLOOR, 0.40, 0.60, 0.80, HI_CEIL])
    ax.set_yticklabels([f"{LO_FLOOR:.2f}", "0.40", "0.60", "0.80", f"{HI_CEIL:.2f}"],
                       fontsize=6, color="#888888")
    ax.set_title("Normalized performance by instance set\n(higher = better)",
                 fontsize=9.5, fontweight="normal", pad=18)

    # Grid styling
    ax.grid(True, alpha=0.15, linewidth=0.4)
    ax.legend(loc="upper right", bbox_to_anchor=(1.18, 1.08),
              framealpha=0.85, borderpad=0.4, fontsize=7.5)

    fig.tight_layout(pad=1.0)
    output_path = SUMMARY_DIR / "summary_radar.png"
    fig.savefig(output_path, facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"Generated radar chart: {output_path}")


def generate_generations_chart(results: dict):
    """Bar chart: avg generations to reach best solution per instance, with std dev error bars."""
    _set_publication_style()

    available = _get_available(results)
    if not available:
        print("Warning: No results available for generations chart.")
        return

    labels = []
    means = []
    stds = []
    colors = []
    for name in available:
        r = results[name]
        gens = r["generations_to_best"]
        if not gens:
            continue
        labels.append(name)
        means.append(np.mean(gens))
        stds.append(np.std(gens))
        colors.append(SET_COLORS[name[0]])

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    x = np.arange(len(labels))

    ax.bar(x, means, color=colors, edgecolor="white", linewidth=0.4, alpha=0.88,
           yerr=stds, error_kw={"capsize": 2.5, "elinewidth": 0.7,
                                "capthick": 0.7, "ecolor": "#555555"})

    # Value labels above bars
    for i, (m, s) in enumerate(zip(means, stds)):
        ax.annotate(f"{m:.0f}±{s:.1f}", (x[i], m + s + max(means) * 0.015),
                    textcoords="data", fontsize=6, ha="center", color="#444444")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Generations")
    ax.set_title("Average generations to reach best solution (mean ± 1 s.d. across 5 runs)",
                 fontsize=9.5, fontweight="normal", pad=10)
    ax.grid(True, axis="y")

    fig.tight_layout(pad=0.6)
    output_path = SUMMARY_DIR / "summary_generations.png"
    fig.savefig(output_path, facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"Generated generations chart: {output_path}")


def generate_route_length_chart(results: dict):
    """Bar chart: average customers per vehicle (route length) for each instance."""
    _set_publication_style()

    available = _get_available(results)
    if not available:
        print("Warning: No results available for route length chart.")
        return

    labels = []
    lengths = []
    colors = []
    for name in available:
        r = results[name]
        routes = r.get("routes", [])
        if not routes:
            continue
        avg_len = sum(len(rt) for rt in routes) / len(routes)
        labels.append(name)
        lengths.append(avg_len)
        colors.append(SET_COLORS[name[0]])

    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    x = np.arange(len(labels))

    ax.bar(x, lengths, color=colors, edgecolor="white", linewidth=0.4, alpha=0.88)

    # Value labels above bars
    for i, v in enumerate(lengths):
        ax.annotate(f"{v:.1f}", (x[i], v),
                    textcoords="offset points", xytext=(0, 3),
                    fontsize=7, ha="center", color="#333333")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Customers per vehicle")
    ax.set_title("Average route length (customers per vehicle) across all instances",
                 fontsize=9.5, fontweight="normal", pad=10)
    ax.grid(True, axis="y")

    fig.tight_layout(pad=0.6)
    output_path = SUMMARY_DIR / "summary_route_length.png"
    fig.savefig(output_path, facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"Generated route length chart: {output_path}")


# =============================================================================
#  Main entry point
# =============================================================================

def generate_plots():
    """Generate all plots for the report."""
    if not RESULTS_FILE.exists():
        print(f"Error: {RESULTS_FILE} not found. Please run run_experiments.py first.")
        return

    with open(RESULTS_FILE) as f:
        results = json.load(f)

    # Ensure output directories exist
    for d in (CONV_DIR, ROUTES_DIR, SUMMARY_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # Individual-instance plots
    print("=" * 60)
    print("1/9  Convergence plots (3 representative instances)")
    print("=" * 60)
    generate_convergence_plots(results)

    print("\n" + "=" * 60)
    print("2/9  Best-route visualization plots (3 representative instances)")
    print("=" * 60)
    generate_route_plots(results)

    # Summary charts (all available instances)
    print("\n" + "=" * 60)
    print("3/9  Summary: best vs BKS (all instances)")
    print("=" * 60)
    generate_summary_chart(results)

    print("\n" + "=" * 60)
    print("4/9  Gap from optimal (all instances)")
    print("=" * 60)
    generate_gap_chart(results)

    print("\n" + "=" * 60)
    print("5/9  Box plot: per-run cost distribution")
    print("=" * 60)
    generate_boxplot(results)

    print("\n" + "=" * 60)
    print("6/9  Runtime vs instance size")
    print("=" * 60)
    generate_runtime_chart(results)

    print("\n" + "=" * 60)
    print("7/9  Radar chart: normalized performance by set")
    print("=" * 60)
    generate_radar_chart(results)

    print("\n" + "=" * 60)
    print("8/9  Generations to best (all instances)")
    print("=" * 60)
    generate_generations_chart(results)

    print("\n" + "=" * 60)
    print("9/9  Route length (all instances)")
    print("=" * 60)
    generate_route_length_chart(results)

    print("\n" + "=" * 60)
    print("All plots generated successfully.")
    print("=" * 60)


if __name__ == "__main__":
    generate_plots()
