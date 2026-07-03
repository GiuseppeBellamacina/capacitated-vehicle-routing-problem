"""VRP instance parser for CVRPLIB format."""

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class CVRPInstance:
    """Represents a CVRP instance."""

    name: str
    comment: str
    dimension: int
    capacity: int
    num_vehicles: int
    edge_weight_type: str
    optimal_value: int | None
    node_coords: list[tuple[int, int]] = field(default_factory=list)
    demands: list[int] = field(default_factory=list)
    depot: int = 0

    @property
    def num_customers(self) -> int:
        """Number of customers (excluding depot)."""
        return self.dimension - 1

    @property
    def coords(self) -> list[tuple[int, int]]:
        """Alias for node_coords."""
        return self.node_coords


def _parse_optimal_from_comment(comment: str) -> int | None:
    """Extract optimal value from comment string if present."""
    import re

    # Matches "Optimal value: 123" or "Best value: 123" (case-insensitive)
    match = re.search(r"(?:Optimal|Best)\s+value:\s*(\d+)", comment, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def read_instance(filepath: str | Path) -> CVRPInstance:
    """Parse a CVRPLIB format instance file."""
    filepath = Path(filepath)

    with open(filepath) as f:
        lines = f.readlines()

    name = ""
    comment = ""
    dimension = 0
    capacity = 0
    edge_weight_type = ""
    node_coords: list[tuple[int, int]] = []
    demands: list[int] = []
    depot = 0

    section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("NAME"):
            name = line.split(":")[1].strip()
        elif line.startswith("COMMENT"):
            comment = line.split(":", 1)[1].strip()
        elif line.startswith("TYPE"):
            pass
        elif line.startswith("DIMENSION"):
            dimension = int(line.split(":")[1].strip())
        elif line.startswith("EDGE_WEIGHT_TYPE"):
            edge_weight_type = line.split(":")[1].strip()
        elif line.startswith("CAPACITY"):
            capacity = int(line.split(":")[1].strip())
        elif line.startswith("NODE_COORD_SECTION"):
            section = "coords"
            continue
        elif line.startswith("DEMAND_SECTION"):
            section = "demands"
            continue
        elif line.startswith("DEPOT_SECTION"):
            section = "depot"
            continue
        elif line == "EOF":
            break

        if section == "coords":
            parts = line.split()
            node_coords.append((int(parts[1]), int(parts[2])))
        elif section == "demands":
            parts = line.split()
            demands.append(int(parts[1]))
        elif section == "depot":
            if line.strip() != "-1":
                depot = int(line.strip()) - 1  # 0-indexed

    # Extract number of vehicles from instance name (e.g., A-n45-k7 -> 7)
    import re

    match = re.search(r"k(\d+)", name)
    num_vehicles = int(match.group(1)) if match else 1

    optimal_value = _parse_optimal_from_comment(comment)

    return CVRPInstance(
        name=name,
        comment=comment,
        dimension=dimension,
        capacity=capacity,
        num_vehicles=num_vehicles,
        edge_weight_type=edge_weight_type,
        optimal_value=optimal_value,
        node_coords=node_coords,
        demands=demands,
        depot=depot,
    )


def compute_distance_matrix(instance: CVRPInstance) -> np.ndarray:
    """Compute Euclidean distance matrix as numpy float64 array."""
    coords = np.array(instance.node_coords, dtype=np.float64)
    n = len(coords)
    dist = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        xi, yi = coords[i]
        for j in range(i + 1, n):
            xj, yj = coords[j]
            d = math.sqrt((xi - xj) ** 2 + (yi - yj) ** 2)
            dist[i, j] = d
            dist[j, i] = d
    return dist
