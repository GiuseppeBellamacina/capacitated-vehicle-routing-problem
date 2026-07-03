"""Quick test script to verify HGA works correctly."""

import sys

sys.path.insert(0, ".")

from cvrp.hga import HybridGeneticAlgorithm
from cvrp.instance import read_instance


def test_instance(name: str):
    instance = read_instance(f"../instances/{name}.vrp")
    print(
        f"Testing {name}: {instance.dimension} nodes, {instance.num_vehicles} vehicles, capacity={instance.capacity}"
    )
    print(f"  Optimal: {instance.optimal_value}")

    hga = HybridGeneticAlgorithm(
        instance=instance,
        population_size=50,
        max_evaluations=2000,
        seed=42,
    )

    solution = hga.run(track_convergence=True)
    print(f"  Best cost: {solution.cost:.2f}")
    print(f"  Routes: {len(solution.routes)}")
    print(f"  Evaluations: {hga.evaluations}")
    print(f"  Generations: {hga.generation}")
    print(f"  Convergence points: {len(hga.best_cost_history)}")

    if instance.optimal_value:
        gap = ((solution.cost - instance.optimal_value) / instance.optimal_value) * 100
        print(f"  Gap: {gap:.2f}%")

    # Verify feasibility
    visited = set()
    for route in solution.routes:
        for node in route:
            if node in visited:
                print(f"  ERROR: Duplicate node {node}!")
            visited.add(node)
    expected = set(range(1, instance.num_customers + 1))
    missing = expected - visited
    if missing:
        print(f"  ERROR: Missing nodes: {missing}")
    else:
        print(f"  All {len(expected)} customers visited [OK]")

    print()


if __name__ == "__main__":
    test_instance("A-n45-k7")
    test_instance("P-n50-k10")
