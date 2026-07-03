"""Utility functions for CVRP solver."""

import json
import math
from collections.abc import Sequence
from pathlib import Path

# ── Shared constants ─────────────────────────────────────────────────────────

DEFAULT_MAX_EVALUATIONS = 350000


def discover_config_results(
    results_root: str | Path | None = None,
) -> dict[str, dict]:
    """Return ``{config_name: results_dict}`` for every results/config_*/results.json.

    Scans subdirectories of *results_root* (defaults to ``results/`` next to
    the project root) and loads each ``results.json`` found.
    """
    if results_root is None:
        results_root = Path(__file__).parent.parent.parent / "results"
    results_root = Path(results_root)
    config_results: dict[str, dict] = {}
    if not results_root.exists():
        return config_results
    for subdir in sorted(results_root.iterdir()):
        if not subdir.is_dir():
            continue
        rf = subdir / "results.json"
        if rf.exists():
            with open(rf) as f:
                config_results[subdir.name] = json.load(f)
    return config_results


def euclidean_distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    """Compute Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def route_cost(
    route: list[int],
    dist_matrix: list[list[float]],
    depot: int = 0,
) -> float:
    """Compute total cost of a single route."""
    if not route:
        return 0.0
    cost = dist_matrix[depot][route[0]]
    for i in range(len(route) - 1):
        cost += dist_matrix[route[i]][route[i + 1]]
    cost += dist_matrix[route[-1]][depot]
    return cost


def solution_cost(
    routes: list[list[int]],
    dist_matrix: list[list[float]],
    depot: int = 0,
) -> float:
    """Compute total cost of all routes."""
    return sum(route_cost(r, dist_matrix, depot) for r in routes)


def route_demand(route: list[int], demands: Sequence[int]) -> int:
    """Compute total demand of a route."""
    return sum(demands[i] for i in route)


def is_feasible(
    routes: list[list[int]],
    demands: Sequence[int],
    capacity: int,
    num_vehicles: int,
    num_customers: int,
) -> bool:
    """Check if a solution is feasible."""
    # Check all customers visited exactly once
    visited = set()
    for route in routes:
        for node in route:
            if node in visited:
                return False
            visited.add(node)
    if visited != set(range(1, num_customers + 1)):
        return False
    # Check capacity constraints
    for route in routes:
        if route_demand(route, demands) > capacity:
            return False
    # Check vehicle limit
    if len(routes) > num_vehicles:
        return False
    return True


def format_routes(routes: list[list[int]]) -> str:
    """Format routes for display (1-indexed)."""
    parts = []
    for i, route in enumerate(routes):
        parts.append(f"  Route {i + 1}: 0 -> {' -> '.join(str(n) for n in route)} -> 0")
    return "\n".join(parts)
