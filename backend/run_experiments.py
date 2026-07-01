"""Full experiment runner: all 10 instances, 5 runs each, 350K evaluations.

Saves results progressively to results.json so partial results survive crashes.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from cvrp.instance import read_instance
from cvrp.hga import HybridGeneticAlgorithm

INSTANCES = [
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

MAX_EVALS = 350_000
RUNS = 5
RESULTS_FILE = Path("results.json")


def load_results() -> dict:
    """Load existing results if any."""
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return {}


def save_results(results: dict):
    """Save results atomically."""
    tmp = RESULTS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(results, f, indent=2)
    tmp.replace(RESULTS_FILE)


def run_instance(instance_name: str) -> dict:
    """Run experiment on a single instance."""
    filepath = Path(f"../instances/{instance_name}.vrp")
    instance = read_instance(filepath)

    print(f"\n{'='*70}")
    print(f"Instance: {instance_name}")
    print(f"  Nodes: {instance.dimension}, Vehicles: {instance.num_vehicles}, "
          f"Capacity: {instance.capacity}")
    print(f"  Optimal: {instance.optimal_value}")
    print(f"{'='*70}")

    all_costs = []
    all_gens = []
    all_convergence = []
    all_vehicles = []
    best_overall = float("inf")
    best_routes = None

    start_time = time.time()

    for run_idx in range(RUNS):
        run_start = time.time()
        print(f"\n  Run {run_idx + 1}/{RUNS}...", end=" ", flush=True)

        hga = HybridGeneticAlgorithm(
            instance=instance,
            population_size=100,
            max_evaluations=MAX_EVALS,
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

        print(f"cost={solution.cost:.2f} {gap_str} "
              f"vehicles={len(solution.routes)} "
              f"gens={solution.generations_to_best} "
              f"time={run_elapsed:.1f}s")

    elapsed = time.time() - start_time
    mean_cost = sum(all_costs) / len(all_costs)
    variance = sum((c - mean_cost) ** 2 for c in all_costs) / len(all_costs)
    std_dev = variance**0.5
    best_cost = min(all_costs)
    mean_gens = sum(all_gens) / len(all_gens)

    gap_to_optimal = ""
    if instance.optimal_value:
        gap_to_optimal = f"{((best_cost - instance.optimal_value) / instance.optimal_value) * 100:.2f}%"

    print(f"\n  Results for {instance_name}:")
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
    results = load_results()

    for name in INSTANCES:
        if name in results:
            print(f"\n[SKIP] {name} already completed")
            continue

        try:
            result = run_instance(name)
            results[name] = result
            save_results(results)
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            save_results(results)  # save what we have

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"{'Instance':<15} {'Best':>10} {'Mean':>10} {'Std Dev':>10} {'Optimal':>10} {'Gap':>8} {'Time':>8}")
    print("-" * 71)
    for name in INSTANCES:
        if name in results:
            r = results[name]
            print(f"{r['name']:<15} {r['best']:>10.2f} {r['mean']:>10.2f} "
                  f"{r['std_dev']:>10.2f} {r['optimal'] or 0:>10} "
                  f"{r['gap']:>8} {r['execution_time']:>7.1f}s")
    save_results(results)
    print(f"\nResults saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
