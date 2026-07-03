"""Quick test script to verify HGA works correctly."""

import sys

sys.path.insert(0, ".")

from cvrp.hga import HybridGeneticAlgorithm
from cvrp.instance import discover_instances, read_instance


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
    instances = discover_instances()
    if instances:
        # Test first instance from each set for quick coverage
        tested_sets: set[str] = set()
        for name in instances:
            set_key = name[0]
            if set_key in ("A", "B", "E", "P") and set_key not in tested_sets:
                tested_sets.add(set_key)
                test_instance(name)
        if not tested_sets:
            # Fallback: test first available
            test_instance(instances[0])
