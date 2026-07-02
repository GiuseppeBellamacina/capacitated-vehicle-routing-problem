"""Script to generate convergence plots from results.json for the LaTeX report."""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import yaml

RESULTS_FILE = Path(__file__).parent.parent / "results" / "results.json"
REPORT_DIR = Path(__file__).parent.parent / "docs" / "report"

# Load max evaluations from config.yaml dynamically
def load_max_evals() -> int:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
            return cfg.get("max_evaluations", 350000)
    return 350000

MAX_EVALS = load_max_evals()

# Select 3 representative instances
REPRESENTATIVE_INSTANCES = [
    "A-n45-k7",
    "E-n76-k8",
    "P-n101-k4"
]

def generate_plots():
    if not RESULTS_FILE.exists():
        print(f"Error: {RESULTS_FILE} not found. Please run run_experiments.py first.")
        return

    with open(RESULTS_FILE) as f:
        results = json.load(f)

    # Ensure report directory exists
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Set matplotlib style for academic quality
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "grid.alpha": 0.3,
        "grid.linestyle": "--"
    })

    for name in REPRESENTATIVE_INSTANCES:
        if name not in results:
            print(f"Warning: {name} results not found in results.json. Skipping.")
            continue

        res = results[name]
        convergence = res["convergence"]
        optimal = res["optimal"]
        
        plt.figure(figsize=(8, 5))
        
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
        
        # 1. Plot individual runs with light gray color
        for run_idx in range(conv_matrix.shape[0]):
            plt.plot(x_vals, conv_matrix[run_idx], color="#bdc3c7", alpha=0.4, linewidth=0.8, label="Individual Runs" if run_idx == 0 else "")
            
        # 2. Plot standard deviation shaded band
        plt.fill_between(x_vals, mean_history - std_history, mean_history + std_history, color="#3498db", alpha=0.15, label="Standard Deviation")
        
        # 3. Plot mean history with a solid blue line
        plt.plot(x_vals, mean_history, color="#2980b9", linewidth=2.0, label="Mean Cost")
        
        # 4. Plot best overall envelope with a green dotted line
        plt.plot(x_vals, min_history, color="#27ae60", linestyle=":", linewidth=1.5, label="Best Run Envelope")

        # 5. Plot optimal line if known
        if optimal:
            plt.axhline(y=optimal, color="#c0392b", linestyle="--", label=f"Optimal ({optimal})", linewidth=1.5)

        plt.title(f"Convergence Curves - Instance {name}")
        plt.xlabel("Fitness Evaluations (FE)")
        plt.ylabel("Best Cost")
        plt.grid(True)
        plt.legend(loc="upper right")
        plt.tight_layout()
        
        output_path = REPORT_DIR / f"convergence_{name}.png"
        plt.savefig(output_path, dpi=300)
        plt.close()
        print(f"Generated plot: {output_path}")

    print("Convergence plotting completed successfully.")

if __name__ == "__main__":
    generate_plots()
