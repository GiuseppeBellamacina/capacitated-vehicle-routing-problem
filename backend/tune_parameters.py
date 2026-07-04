"""Optuna hyperparameter tuning for CVRP HGA.

Searches for the best HGA parameters by running short experiments (50k evals,
1 run) on representative instances. Uses TPE sampler with warm-start from
known-good default parameters.

Usage:
    # Quick test with 20 trials
    python tune_parameters.py --trials 20

    # Use config file (recommended for cluster runs)
    python tune_parameters.py --config ../config/config_optuna.yaml

    # Config file + CLI override
    python tune_parameters.py --config ../config/config_optuna.yaml --trials 50

    # Resume a previous study
    python tune_parameters.py --trials 100 --study-name hga_tuning_v1 --storage sqlite:///tuning.db

    # Tune on specific instances
    python tune_parameters.py --trials 50 --instances A-n45-k7 B-n66-k9

    # Use a different per-trial budget
    python tune_parameters.py --trials 50 --budget 75000
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import optuna
import yaml

sys.path.insert(0, ".")

from cvrp.hga import HybridGeneticAlgorithm
from cvrp.instance import get_representative_instances, read_instance

# ── Search space configuration ──────────────────────────────────────────────

# Default known-good parameters used for warm-start
DEFAULT_PARAMS = {
    "population_size": 100,
    "tournament_size": 4,
    "crossover_rate": 0.8,
    "mutation_rate": 0.1,
    "local_search_rate": 0.1,
    "elite_count": 5,
    "local_search_max_iter": 2,
    "granular_size": 15,
}

# Per-trial evaluation budget (much smaller than full experiment 350k)
DEFAULT_BUDGET = 50_000

# Seed base for reproducibility within a trial
SEED_BASE = 12345


# ── Objective function ──────────────────────────────────────────────────────


def objective(
    trial: optuna.Trial, instances: list[str], budget: int, runs_per_trial: int = 1
) -> float:
    """Optuna objective: minimize mean gap across tuning instances.

    Args:
        trial: Optuna trial object.
        instances: List of instance names to evaluate on (e.g., ['A-n45-k7', 'B-n66-k9']).
        budget: Max evaluations per trial (e.g., 50000).
        runs_per_trial: Number of independent runs per instance (default 1 for speed).

    Returns:
        Mean gap (0+ = above optimal, negative = below if optimal unknown).
    """
    # ── Suggest hyperparameters ──────────────────────────────────────────
    pop_size = trial.suggest_int("population_size", 20, 150)

    params = {
        "population_size": pop_size,
        "tournament_size": trial.suggest_int("tournament_size", 2, 5),
        "crossover_rate": trial.suggest_float("crossover_rate", 0.5, 1.0),
        "mutation_rate": trial.suggest_float("mutation_rate", 0.01, 0.5, log=True),
        "local_search_rate": trial.suggest_float(
            "local_search_rate", 0.01, 0.3, log=True
        ),
        "elite_count": trial.suggest_int("elite_count", 0, max(1, pop_size // 10)),
        "local_search_max_iter": trial.suggest_int("local_search_max_iter", 1, 10),
        "granular_size": trial.suggest_int("granular_size", 10, 40),
    }

    gaps: list[float] = []

    instances_dir = Path(__file__).parent.parent / "instances"

    for instance_name in instances:
        instance = read_instance(instances_dir / f"{instance_name}.vrp")
        opt_val = instance.optimal_value

        trial_costs: list[float] = []
        for run_idx in range(runs_per_trial):
            seed = SEED_BASE + trial.number * 100 + run_idx * 42

            hga = HybridGeneticAlgorithm(
                instance=instance,
                max_evaluations=budget,
                population_size=params["population_size"],
                tournament_size=params["tournament_size"],
                crossover_rate=params["crossover_rate"],
                mutation_rate=params["mutation_rate"],
                local_search_rate=params["local_search_rate"],
                elite_count=params["elite_count"],
                local_search_max_iter=params["local_search_max_iter"],
                granular_size=params["granular_size"],
                seed=seed,
            )

            solution = hga.run(track_convergence=False)
            trial_costs.append(solution.cost)

        best_cost = min(trial_costs)

        # Gap: positive = above optimal, 0 = optimal reached
        if opt_val:
            gap = (best_cost - opt_val) / opt_val
        else:
            # No optimal known, use best cost as-is (normalized by itself = 0)
            gap = 0.0

        gaps.append(gap)

    # Return mean gap (minimize)
    mean_gap = float(np.mean(gaps))

    # Report per-instance gaps for study analysis
    for i, instance_name in enumerate(instances):
        trial.set_user_attr(f"gap_{instance_name}", gaps[i])

    return mean_gap


# ── CLI ─────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optuna hyperparameter tuning for CVRP HGA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tune_parameters.py --trials 50
  python tune_parameters.py --config ../config/config_optuna.yaml
  python tune_parameters.py --config ../config/config_optuna.yaml --trials 30
  python tune_parameters.py --trials 50 --instances A-n45-k7 B-n66-k9
  python tune_parameters.py --study-name hga_v1 --storage sqlite:///tuning.db
        """,
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to Optuna tuning config YAML (e.g., config/config_optuna.yaml). "
        "CLI arguments override YAML values.",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=None,
        help="Number of Optuna trials (default: 30, or from YAML config)",
    )
    parser.add_argument(
        "--study-name",
        default=None,
        help="Optuna study name (default: hga_tuning, or from YAML config)",
    )
    parser.add_argument(
        "--storage",
        default=None,
        help="Optuna storage URL (default: None = in-memory). "
        "Use e.g. 'sqlite:///tuning.db' to persist.",
    )
    parser.add_argument(
        "--instances",
        nargs="*",
        default=None,
        help="Instance names to tune on (default: representative instances, one per set)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help=f"Max evaluations per trial (default: {DEFAULT_BUDGET}, or from YAML config)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Independent runs per instance per trial (default: 1, or from YAML config)",
    )
    parser.add_argument(
        "--no-warm-start",
        action="store_true",
        default=None,
        help="Disable warm-start with default parameters",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save best params as YAML config file (e.g., config/config_tuned.yaml)",
    )
    return parser.parse_args()


def load_config_yaml(config_path: str) -> dict:
    """Load Optuna tuning parameters from a YAML config file."""
    path = Path(config_path)
    if not path.exists():
        print(f"Error: config file not found: {path}")
        sys.exit(1)
    try:
        with open(path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: invalid YAML in config file '{path}':\n{e}")
        sys.exit(1)
    if not isinstance(config, dict):
        print(
            f"Error: config file '{path}' is empty or does not contain a YAML mapping."
        )
        sys.exit(1)
    return config


def resolve_args(args: argparse.Namespace) -> dict:
    """Merge YAML config (if any) with CLI args (CLI overrides YAML).

    Returns a dict of resolved parameters. All paths are resolved relative
    to the project root (parent of this file's directory).
    """
    PROJ_ROOT = Path(__file__).parent.parent

    # Start with YAML config defaults, or empty
    yaml_cfg: dict = {}
    if args.config:
        yaml_cfg = load_config_yaml(args.config)

    # Map YAML keys to CLI arg names (with CLI taking precedence)
    def _get(key: str, cli_val, default_val):
        if cli_val is not None:
            return cli_val
        if key in yaml_cfg:
            return yaml_cfg[key]
        return default_val

    # Handle warm_start separately (boolean with negation from --no-warm-start)
    if args.no_warm_start is True:
        warm_start = False
    elif args.no_warm_start is False:
        warm_start = True
    elif "warm_start" in yaml_cfg:
        warm_start = yaml_cfg["warm_start"]
    else:
        warm_start = True

    # Resolve output_config relative to project root
    output_config_raw = _get("output_config", args.output, None)
    output_config = None
    if output_config_raw:
        output_config = str(PROJ_ROOT / output_config_raw)

    # Resolve output_dir relative to project root
    output_dir_raw = _get("output_dir", None, "results/tuning")
    output_dir = str(PROJ_ROOT / output_dir_raw)

    # Resolve storage path relative to project root (if it's a relative sqlite URL)
    storage = _get("storage", args.storage, None)
    if (
        storage
        and storage.startswith("sqlite:///")
        and not storage.startswith("sqlite:////")
    ):
        rel_path = storage[len("sqlite:///") :]
        abs_path = str(PROJ_ROOT / rel_path)
        storage = f"sqlite:///{abs_path}"

    resolved = {
        "study_name": _get("study_name", args.study_name, "hga_tuning"),
        "trials": _get("trials", args.trials, 30),
        "storage": storage,
        "budget": _get("budget", args.budget, DEFAULT_BUDGET),
        "runs": _get("runs_per_trial", args.runs, 1),
        "warm_start": warm_start,
        "output": output_config,
        "output_dir": output_dir,
        "instances": (
            args.instances if args.instances is not None else yaml_cfg.get("instances")
        ),
    }

    return resolved


def main():
    args = parse_args()
    cfg = resolve_args(args)

    # ── Resolve instances ─────────────────────────────────────────────────
    instances = cfg["instances"] if cfg["instances"] else get_representative_instances()

    # ── Create output directory ───────────────────────────────────────────
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.config:
        print(f"Config file:         {args.config}")
    print(f"Output dir:          {output_dir}")
    print(f"Tuning on instances: {', '.join(instances)}")
    print(f"Per-trial budget:    {cfg['budget']:,} evaluations")
    print(f"Runs per instance:   {cfg['runs']}")
    print(f"Trials:              {cfg['trials']}")
    print(f"Study name:          {cfg['study_name']}")
    if cfg["storage"]:
        print(f"Storage:             {cfg['storage']}")
    if cfg["output"]:
        print(f"Output config:       {cfg['output']}")
    print()

    # ── Create study ──────────────────────────────────────────────────────
    sampler = optuna.samplers.TPESampler(multivariate=True, seed=42)
    study = optuna.create_study(
        study_name=cfg["study_name"],
        storage=cfg["storage"],
        direction="minimize",
        sampler=sampler,
        load_if_exists=True,
    )

    is_fresh = len(study.trials) == 0

    # ── Warm-start with default params ────────────────────────────────────
    if cfg["warm_start"] and is_fresh:
        study.enqueue_trial(DEFAULT_PARAMS)
        print("Warm-start: enqueued default parameters.")

    n_trials = cfg["trials"]

    # ── Periodic summary saver (called every 5 trials) ──────────────────
    summary_file = output_dir / "tuning_summary.json"

    def save_summary():
        completed = [t for t in study.trials if t.value is not None]
        completed_sorted = sorted(completed, key=lambda t: t.value)  # type: ignore[reportArgumentType,reportCallIssue]
        summary = {
            "study_name": cfg["study_name"],
            "elapsed_seconds": time.time() - start_time,
            "n_trials": n_trials,
            "n_completed": len(completed),
            "best_value": study.best_value,
            "best_params": study.best_params,
            "tuning_instances": instances,
            "per_trial_budget": cfg["budget"],
            "runs_per_instance": cfg["runs"],
            "top_trials": [],
        }
        for i, t in enumerate(completed_sorted[:5]):
            summary["top_trials"].append(
                {
                    "rank": i + 1,
                    "trial_number": t.number,
                    "value": t.value,
                    "params": t.params,
                }
            )
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2, default=str)

    # ── Progress callback ─────────────────────────────────────────────────
    def progress_callback(study: optuna.Study, trial: optuna.trial.FrozenTrial):
        if trial.value is not None:
            pct = (
                len(
                    [
                        t
                        for t in study.trials
                        if t.state == optuna.trial.TrialState.COMPLETE
                    ]
                )
                / n_trials
            ) * 100
            print(
                f"  Trial {trial.number:3d} | "
                f"mean_gap={trial.value:.4f} | "
                f"progress={pct:.0f}% | "
                f"best={study.best_value:.4f}"
            )

            # Periodic save every 5 completed trials (crash-safe)
            if trial.number > 0 and trial.number % 5 == 0:
                save_summary()
                print(f"  💾 Checkpoint saved to {summary_file}")

    # ── Run optimization ──────────────────────────────────────────────────
    start_time = time.time()

    try:
        study.optimize(
            lambda trial: objective(trial, instances, cfg["budget"], cfg["runs"]),
            n_trials=n_trials,
            callbacks=[progress_callback],
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")

    elapsed = time.time() - start_time

    # ── Report results ────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("TUNING COMPLETE")
    print(f"{'='*70}")
    print(f"Time:           {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(
        f"Completed:      {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}/{n_trials}"
    )
    print(f"Best mean gap:  {study.best_value:.6f}")
    print("Best params:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")
    print()

    # ── Show top-5 trials ─────────────────────────────────────────────────
    print("Top 5 trials:")
    completed = [t for t in study.trials if t.value is not None]
    completed.sort(key=lambda t: t.value)  # type: ignore[reportArgumentType,reportCallIssue]
    for i, t in enumerate(completed[:5]):
        print(
            f"  #{i+1}: gap={t.value:.6f} | pop={t.params['population_size']} "
            f"mut={t.params['mutation_rate']:.3f} ls={t.params['local_search_rate']:.3f} "
            f"tour={t.params['tournament_size']} elite={t.params['elite_count']} "
            f"gran={t.params['granular_size']}"
        )

    # ── Save best config as YAML if requested ─────────────────────────────
    if cfg["output"] and study.best_params:
        output_path = Path(cfg["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "population_size": study.best_params["population_size"],
            "max_evaluations": 350000,  # Full budget for production runs
            "runs": 5,
            "crossover_rate": study.best_params["crossover_rate"],
            "mutation_rate": study.best_params["mutation_rate"],
            "local_search_rate": study.best_params["local_search_rate"],
            "tournament_size": study.best_params["tournament_size"],
            "elite_count": study.best_params["elite_count"],
            "local_search_max_iter": study.best_params["local_search_max_iter"],
            "granular_size": study.best_params["granular_size"],
        }

        # Derive output paths from the config filename
        config_name = output_path.stem  # e.g., "config_tuned"
        config["output_dir"] = f"results/{config_name}"
        config["imgs_dir"] = f"docs/report/imgs/{config_name}"

        with open(output_path, "w") as f:
            f.write(
                f"# ==============================================================================\n"
                f'# CONFIGURAZIONE HGA — Variante "Optuna" (parametri ottimizzati da Optuna)\n'
                f"# ==============================================================================\n"
                f"# Studio: {cfg['study_name']}\n"
                f"# Best mean gap: {study.best_value:.6f}\n"
                f"# Trials: {len(completed)}\n"
                f"# Tuning instances: {', '.join(instances)}\n"
                f"\n"
            )
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"\nBest config saved to {output_path}")

    # ── Final tuning summary save ────────────────────────────────────────
    save_summary()
    print(f"Tuning summary saved to {summary_file}")


if __name__ == "__main__":
    main()
