"""Script to generate convergence plots from results.json for the LaTeX report."""

import json
from pathlib import Path
import matplotlib.pyplot as plt
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
        
        # Plot each run
        for run_idx, run_history in enumerate(convergence):
            L = len(run_history)
            if L > 1:
                x_vals = [i * (MAX_EVALS / (L - 1)) for i in range(L)]
            else:
                x_vals = [0]
            plt.plot(x_vals, run_history, label=f"Run {run_idx + 1}", linewidth=1.5, alpha=0.8)

        # Plot optimal line if known
        if optimal:
            plt.axhline(y=optimal, color="r", linestyle="--", label=f"Optimal ({optimal})", linewidth=1.2)

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
