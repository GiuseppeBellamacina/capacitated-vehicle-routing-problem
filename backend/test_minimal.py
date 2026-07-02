"""Minimal test to diagnose numba HGA issues."""
import sys
import time
sys.path.insert(0, ".")

print("Importing numba_utils...")
t0 = time.time()
from cvrp.numba_utils import split_numba, two_opt_numba
print(f"  Import done in {time.time()-t0:.1f}s")

import numpy as np

# Test two_opt_numba directly
print("Testing two_opt_numba...")
t0 = time.time()
dist = np.random.rand(50, 50).astype(np.float64)
dist = (dist + dist.T) / 2
np.fill_diagonal(dist, 0)
route = np.arange(1, 11, dtype=np.int32)
np.random.shuffle(route)
print(f"  Input route: {route}")
t1 = time.time()
result = two_opt_numba(route, dist, 0)
print(f"  two_opt completed in {time.time()-t1:.1f}s, result: {result}")
print(f"  Total test time: {time.time()-t0:.1f}s")

# Test split_numba directly
print("\nTesting split_numba...")
t0 = time.time()
perm = np.random.permutation(np.arange(1, 45, dtype=np.int32))
demands = np.ones(50, dtype=np.int32)
demands[0] = 0
for i in range(1, 45):
    demands[i] = (i % 20) + 1

t1 = time.time()
routes_flat, route_ends, num_routes, cost = split_numba(perm, dist, demands, 100, 0)
print(f"  split completed in {time.time()-t1:.1f}s")
print(f"  Cost: {cost:.2f}, Routes: {num_routes}")

# Now test full HGA
print("\nTesting full HGA on A-n45-k7...")
t0 = time.time()
from cvrp.instance import read_instance
from cvrp.hga import HybridGeneticAlgorithm

instance = read_instance("../instances/A-n45-k7.vrp")
print(f"  Instance loaded: {instance.name}, {instance.num_customers} customers")

def progress_callback(data):
    print(f"  [Callback] Gen {data['generation']}: Evals {data['evaluations']}/{hga.max_evaluations}, Best Cost: {data['best_cost']:.2f}")

print("  Initializing HGA object...")
hga = HybridGeneticAlgorithm(
    instance=instance,
    population_size=20,
    max_evaluations=500,
    seed=42,
    callback=progress_callback,
)

print("  Starting HGA evolution loop (hga.run)...")
t1 = time.time()
solution = hga.run(track_convergence=True)
elapsed = time.time() - t0
print(f"  Total HGA time: {elapsed:.1f}s")
print(f"  Best cost: {solution.cost:.2f} (optimal: {instance.optimal_value})")
print(f"  Routes: {len(solution.routes)}")
print(f"  Evaluations: {hga.evaluations}")

# Verify
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

print("\nALL TESTS PASSED!")
