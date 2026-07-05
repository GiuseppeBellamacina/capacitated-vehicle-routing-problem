"""Run CVRP HGA experiments on all benchmark instances.

Usage:
    python run_experiments.py --config ../config/config_small.yaml
"""

import argparse
import json
import sys
import time
from pathlib import Path

import yaml  # noqa: E402

sys.path.insert(0, ".")

from cvrp.hga import HybridGeneticAlgorithm
from cvrp.instance import discover_instances, read_instance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CVRP HGA experiments")
    parser.add_argument(
        "--config",
        default="../config/config.yaml",
        help="Path to config YAML file (default: ../config/config.yaml)",
    )
    return parser.parse_args()


def load_config(config_path: str) -> dict:
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
        print(f"Error: config file '{path}' is empty or does not contain a YAML mapping.")
        sys.exit(1)
    return config


def load_results(results_file: Path) -> dict:
    if results_file.exists():
        with open(results_file) as f:
            return json.load(f)
    return {}


def save_results(results: dict, results_file: Path):
    tmp = results_file.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(results, f, indent=2)
    tmp.replace(results_file)


def run_instance(instance_name: str, config: dict, max_evals: int, runs: int) -> dict:
    filepath = Path(f"../instances/{instance_name}.vrp")
    instance = read_instance(filepath)

    print(f"\n{'='*70}")
    print(f"Instance: {instance_name}")
    print(
        f"  Nodes: {instance.dimension}, Vehicles: {instance.num_vehicles}, "
        f"Capacity: {instance.capacity}"
    )
    print(f"  Optimal: {instance.optimal_value}")
    print(f"{'='*70}")

    all_costs = []
    all_gens = []
    all_convergence = []
    all_vehicles = []
    best_overall = float("inf")
    best_routes = None

    start_time = time.time()

    from tqdm import tqdm

    run_bar = tqdm(range(runs), desc=f"  Runs on {instance_name}", unit="run")
    for run_idx in run_bar:
        run_start = time.time()

        hga = HybridGeneticAlgorithm(
            instance=instance,
            population_size=config.get("population_size", 100),
            max_evaluations=max_evals,
            crossover_rate=config.get("crossover_rate", 0.8),
            mutation_rate=config.get("mutation_rate", 0.1),
            local_search_rate=config.get("local_search_rate", 0.1),
            tournament_size=config.get("tournament_size", 2),
            elite_count=config.get("elite_count", 2),
            local_search_max_iter=config.get("local_search_max_iter", 2),
            granular_size=config.get("granular_size", 15),
            seed=run_idx * 42 + 12345,
        )

        solution = hga.run(track_convergence=True)
        run_elapsed = time.time() - run_start

        all_costs.append(solution.cost)
        all_gens.append(solution.generations_to_best)
        all_convergence.append(hga.best_cost_history[:])
        all_vehicles.append(len(solution.routes))

        if solution.cost < best_overall:
            best_overall = solution.cost
            best_routes = solution.routes

        gap_str = ""
        if instance.optimal_value:
            gap = ((solution.cost - instance.optimal_value) / instance.optimal_value) * 100
            gap_str = f"gap={gap:.2f}%"

        run_bar.write(
            f"    Run {run_idx + 1}/{runs}: cost={solution.cost:.2f} {gap_str} "
            f"vehicles={len(solution.routes)} gens={solution.generations_to_best} "
            f"time={run_elapsed:.1f}s"
        )

    elapsed = time.time() - start_time
    mean_cost = sum(all_costs) / len(all_costs)
    variance = sum((c - mean_cost) ** 2 for c in all_costs) / len(all_costs)
    std_dev = variance**0.5
    best_cost = min(all_costs)
    mean_gens = sum(all_gens) / len(all_gens)

    gap_to_optimal = ""
    if instance.optimal_value:
        gap_to_optimal = (
            f"{((best_cost - instance.optimal_value) / instance.optimal_value) * 100:.2f}%"
        )

    print(f"\n  Results for {instance_name}:")
    print(f"    Optimal:  {instance.optimal_value}")
    print(f"    Best:     {best_cost:.2f} ({gap_to_optimal})")
    print(f"    Mean:     {mean_cost:.2f}")
    print(f"    Std Dev:  {std_dev:.2f}")
    print(f"    Avg Gens: {mean_gens:.1f}")
    print(f"    Time:     {elapsed:.1f}s")

    return {
        "name": instance_name,
        "optimal": instance.optimal_value,
        "best": best_cost,
        "mean": mean_cost,
        "std_dev": std_dev,
        "per_run_costs": all_costs,
        "generations_to_best": all_gens,
        "num_vehicles": all_vehicles,
        "convergence": all_convergence,
        "execution_time": elapsed,
        "routes": [[int(n) for n in r] for r in (best_routes or [])],
        "gap": gap_to_optimal,
        "dimension": instance.dimension,
        "num_vehicles_config": instance.num_vehicles,
    }


def main():
    args = parse_args()
    config = load_config(args.config)

    max_evals = config.get("max_evaluations", 350000)
    runs = config.get("runs", 5)

    # Output path comes from the config file itself
    output_dir = config.get("output_dir", "results")
    results_file = Path(__file__).parent.parent / output_dir / "results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Config:   {args.config}")
    print(f"Output:   {results_file}")
    print(f"Pop size: {config.get('population_size', '?')}")
    print(f"Max FE:   {max_evals}")
    print(f"Runs:     {runs}")

    all_results = load_results(results_file)
    instances = discover_instances()

    for name in instances:
        if name in all_results:
            print(f"\n[SKIP] {name} already completed")
            continue

        try:
            result = run_instance(name, config, max_evals, runs)
            all_results[name] = result
            save_results(all_results, results_file)
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            import traceback

            traceback.print_exc()
            save_results(all_results, results_file)

    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(
        f"{'Instance':<15} {'Best':>10} {'Mean':>10} {'Std Dev':>10} {'Optimal':>10} {'Gap':>8} {'Time':>8}"
    )
    print("-" * 71)
    for name in instances:
        if name in all_results:
            r = all_results[name]
            print(
                f"{r['name']:<15} {r['best']:>10.2f} {r['mean']:>10.2f} "
                f"{r['std_dev']:>10.2f} {r['optimal'] or 0:>10} "
                f"{r['gap']:>8} {r['execution_time']:>7.1f}s"
            )
    save_results(all_results, results_file)
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    main()
