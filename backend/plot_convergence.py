"""Script to generate convergence plots and best-route visualizations from results.json."""

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
REPORT_DIR = Path(__file__).parent.parent / "docs" / "report"
INSTANCES_DIR = Path(__file__).parent.parent / "instances"

# Load max evaluations from config.yaml dynamically
def load_max_evals() -> int:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
            return cfg.get("max_evaluations", 350000)
    return 350000

MAX_EVALS = load_max_evals()

# Select 3 representative instances (one per set A, E, P)
REPRESENTATIVE_INSTANCES = [
    "A-n45-k7",
    "E-n76-k8",
    "P-n101-k4"
]

# Color palette for routes — elegant, colorblind-friendly, publication-quality
# Based on the Tol Vibrant qualitative scheme
ROUTE_COLORS = [
    "#0077BB", "#EE7733", "#009988", "#EE3377", "#33BBEE",
    "#CC3311", "#BBBBBB", "#AA3377", "#228833", "#4477AA",
    "#DDCC77", "#66CCEE", "#885522", "#CCBB44", "#AA4466",
    "#77AADD", "#99DDBB", "#DDAA33", "#5533AA", "#BB6644",
]


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

        # ---- Create figure ----
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

        # 1. Individual runs — subtle gray, very light
        for run_idx in range(conv_matrix.shape[0]):
            ax.plot(x_vals, conv_matrix[run_idx], color="#cccccc", alpha=0.35,
                    linewidth=0.6, label="Individual runs" if run_idx == 0 else "")

        # 2. Standard deviation band — soft blue fill
        ax.fill_between(x_vals, mean_history - std_history, mean_history + std_history,
                        color="#0077BB", alpha=0.10, label="±1 s.d.")

        # 3. Mean history — solid, prominent
        ax.plot(x_vals, mean_history, color="#0077BB", linewidth=1.6, label="Mean")

        # 4. Best envelope — dashed
        ax.plot(x_vals, min_history, color="#009988", linestyle="--", linewidth=1.2,
                label="Best")

        # 5. Optimal reference line
        if optimal:
            ax.axhline(y=optimal, color="#CC3311", linestyle=":", linewidth=1.2,
                       label=f"BKS ({optimal})")

        # ---- Title ----
        gap_str = ""
        if optimal:
            gap = ((best_cost - optimal) / optimal) * 100
            gap_str = f" (gap {gap:+.2f}%)"
        ax.set_title(
            f"{name}  —  Convergence  |  "
            f"Best: {best_cost:.0f}{gap_str}  |  "
            f"Runs: {conv_matrix.shape[0]}",
            fontsize=9.5,
            fontweight="normal",
            loc="center",
            pad=10,
        )

        # ---- Axis labels ----
        ax.set_xlabel("Fitness evaluations (FE)")
        ax.set_ylabel("Cost")
        ax.grid(True)

        # ---- Legend ----
        ax.legend(loc="upper right", framealpha=0.85, borderpad=0.4,
                  handlelength=1.6, handletextpad=0.5)

        # ---- Format x-axis with thousands separator ----
        ax.ticklabel_format(axis="x", style="scientific", scilimits=(3, 4))

        fig.tight_layout(pad=0.5)

        output_path = REPORT_DIR / f"convergence_{name}.png"
        fig.savefig(output_path, facecolor="white", edgecolor="none")
        plt.close(fig)
        print(f"Generated convergence plot: {output_path}")


def generate_route_plots(results: dict):
    """Generate publication-quality best-route visualization on 2D coordinate maps."""
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

        # Read instance
        instance = read_instance(instance_path)
        coords = instance.node_coords
        depot_idx = instance.depot
        demands = instance.demands

        best_cost = res["best"]
        optimal = res.get("optimal")
        num_vehicles_used = len(routes)

        # --- Create figure with golden-ratio proportions ---
        fig, ax = plt.subplots(figsize=(6.0, 6.0 * 0.75))

        # Compute axis limits with 6% padding
        depot_x, depot_y = coords[depot_idx]
        all_x = [c[0] for c in coords]
        all_y = [c[1] for c in coords]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        x_pad = (x_max - x_min) * 0.06 + 2
        y_pad = (y_max - y_min) * 0.06 + 2
        ax.set_xlim(x_min - x_pad, x_max + x_pad)
        ax.set_ylim(y_min - y_pad, y_max + y_pad)

        # ---- Draw route edges (curved, with arrows) ----
        # Use FancyArrowPatch with arc3 connectionstyle for reliable curved arrows
        for ri, route in enumerate(routes):
            color = ROUTE_COLORS[ri % len(ROUTE_COLORS)]

            # Build full path nodes: depot -> route[0] -> ... -> route[-1] -> depot
            path_nodes = [depot_idx] + route + [depot_idx]
            n_seg = len(path_nodes) - 1

            for si in range(n_seg):
                x0, y0 = coords[path_nodes[si]]
                x1, y1 = coords[path_nodes[si + 1]]

                # Alternate curvature direction between adjacent segments
                rad_sign = 1 if si % 2 == 0 else -1
                patch = FancyArrowPatch(
                    posA=(x0, y0),
                    posB=(x1, y1),
                    arrowstyle="-|>",
                    mutation_scale=6,
                    connectionstyle=f"arc3,rad={rad_sign * 0.10}",
                    color=color,
                    linewidth=1.2,
                    alpha=0.82,
                    zorder=3,
                    joinstyle="round",
                    capstyle="round",
                )
                ax.add_patch(patch)

        # ---- Draw customer nodes (sized by demand) ----
        # Collect all customer coords and demand values
        customer_nodes: list[int] = []
        for route in routes:
            for n in route:
                if n not in customer_nodes:
                    customer_nodes.append(n)

        cx_vals = [coords[n][0] for n in customer_nodes]
        cy_vals = [coords[n][1] for n in customer_nodes]
        demand_vals = np.array([demands[n] for n in customer_nodes], dtype=float)

        # Scale marker sizes: min 18, max 120 points², scaled by demand percentile
        d_min, d_max = demand_vals.min(), demand_vals.max()
        if d_max > d_min:
            sizes = 18 + (demand_vals - d_min) / (d_max - d_min) * 102
        else:
            sizes = np.full_like(demand_vals, 35.0)

        ax.scatter(cx_vals, cy_vals, s=sizes, c="#444444", marker="o",
                   zorder=4, edgecolors="white", linewidths=0.5,
                   alpha=0.88, label="Customer")

        # ---- Draw depot (prominent marker) ----
        ax.scatter([depot_x], [depot_y], c="#CC3311", marker="D", s=100,
                   zorder=6, edgecolors="#661100", linewidths=1.2,
                   label="Depot")

        # ---- Route labels placed at the midpoint of each route's first edge ----
        for ri, route in enumerate(routes):
            if not route:
                continue
            color = ROUTE_COLORS[ri % len(ROUTE_COLORS)]
            # Place label at the midpoint of the first customer node
            first = route[0]
            mid_x = (depot_x + coords[first][0]) / 2
            mid_y = (depot_y + coords[first][1]) / 2
            # Offset perpendicular to depot→first edge
            dx_edge = coords[first][0] - depot_x
            dy_edge = coords[first][1] - depot_y
            norm = np.hypot(dx_edge, dy_edge) or 1.0
            offset_x = -dy_edge / norm * 6
            offset_y = dx_edge / norm * 6
            ax.annotate(
                f"{ri + 1}",
                (mid_x, mid_y),
                textcoords="offset points",
                xytext=(offset_x, offset_y),
                fontsize=6.5,
                fontweight="bold",
                color=color,
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="circle,pad=0.15",
                    facecolor="white",
                    edgecolor=color,
                    linewidth=0.9,
                    alpha=0.92,
                ),
                zorder=7,
            )

        # ---- Demand size legend (small / medium / large) ----
        if d_max > d_min:
            legend_demands = [d_min, (d_min + d_max) / 2, d_max]
            legend_sizes = [
                18 + (d - d_min) / (d_max - d_min) * 102 for d in legend_demands
            ]
            legend_handles = []
            for d_val, s_val in zip(legend_demands, legend_sizes):
                legend_handles.append(
                    Line2D(
                        [0], [0],
                        marker="o",
                        color="none",
                        markerfacecolor="#444444",
                        markeredgecolor="white",
                        markeredgewidth=0.5,
                        markersize=np.sqrt(s_val),
                        alpha=0.88,
                        label=f"{int(d_val)}",
                    )
                )
            legend1 = ax.legend(
                handles=legend_handles,
                loc="lower left",
                title="Demand",
                title_fontsize=7,
                framealpha=0.85,
                borderpad=0.5,
                handletextpad=0.6,
            )
            ax.add_artist(legend1)

        # ---- Depot legend ----
        depot_handle = Line2D(
            [0], [0],
            marker="D",
            color="none",
            markerfacecolor="#CC3311",
            markeredgecolor="#661100",
            markeredgewidth=1.0,
            markersize=7.5,
        )
        ax.legend(
            handles=[depot_handle],
            labels=["Depot"],
            loc="lower right",
            framealpha=0.85,
            borderpad=0.5,
        )

        # ---- Title ----
        title_line1 = f"{name}  —  Best solution"
        gap_str = ""
        if optimal:
            gap = ((best_cost - optimal) / optimal) * 100
            gap_str = f" (gap {gap:+.2f}%)"
        title_line2 = (
            f"Cost: {best_cost:.0f}{gap_str}    "
            f"Vehicles: {num_vehicles_used}/{instance.num_vehicles}    "
            f"Customers: {len(customer_nodes)}"
        )
        ax.set_title(
            f"{title_line1}\n{title_line2}",
            fontsize=9.5,
            fontweight="normal",
            loc="center",
            pad=10,
            linespacing=1.4,
        )

        # ---- Axis labels ----
        ax.set_xlabel("x-coordinate")
        ax.set_ylabel("y-coordinate")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.12, linewidth=0.4)

        # ---- Save ----
        output_path = REPORT_DIR / f"routes_{name}.png"
        fig.savefig(output_path, dpi=300, bbox_inches="tight", pad_inches=0.08,
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        print(f"Generated route plot: {output_path}")


def generate_plots():
    """Generate both convergence and route visualization plots."""
    if not RESULTS_FILE.exists():
        print(f"Error: {RESULTS_FILE} not found. Please run run_experiments.py first.")
        return

    with open(RESULTS_FILE) as f:
        results = json.load(f)

    # Ensure report directory exists
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Generating convergence plots...")
    print("=" * 60)
    generate_convergence_plots(results)

    print("\n" + "=" * 60)
    print("Generating best-route visualization plots...")
    print("=" * 60)
    generate_route_plots(results)

    print("\n" + "=" * 60)
    print("All plots generated successfully.")
    print("=" * 60)


if __name__ == "__main__":
    generate_plots()
