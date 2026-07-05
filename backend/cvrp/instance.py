"""VRP instance parser for CVRPLIB format."""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ── Instance discovery ───────────────────────────────────────────────────────

_INSTANCES_DIR = Path(__file__).parent.parent.parent / "instances"


def discover_instances(instances_dir: str | Path | None = None) -> list[str]:
    """Auto-discover all .vrp files, returning sorted instance names.

    Scans the instances/ directory for ``*.vrp`` files and returns their
    stem (name without extension) sorted alphabetically.  New instances
    are automatically picked up — no hardcoded lists needed.
    """
    if instances_dir is None:
        instances_dir = _INSTANCES_DIR
    return sorted(p.stem for p in Path(instances_dir).glob("*.vrp"))


def get_representative_instances(
    instances_dir: str | Path | None = None,
) -> list[str]:
    """Return one representative instance per set, varying depth per set.

    Groups instances by first letter (alphabetically, no hardcoded letters),
    sorts each group numerically by node count, then picks a *different
    index* within each group:

    * Group 0 → index 0 (smallest instance)
    * Group 1 → index 1 (second smallest)
    * Group 2 → index 2 (third smallest)
    * … and so on.

    If a group has fewer instances than the requested index, the *largest*
    instance in that group is used instead.
    """
    all_instances = discover_instances(instances_dir)

    # Group by first letter
    groups: dict[str, list[str]] = {}
    for name in all_instances:
        groups.setdefault(name[0], []).append(name)

    # Sort each group by node count (numeric, not alphabetical)
    for key in groups:
        groups[key].sort(key=lambda n: int(m.group(1)) if (m := re.search(r"-n(\d+)-", n)) else 0)

    sorted_keys = sorted(groups.keys())
    representatives: list[str] = []
    for gi, key in enumerate(sorted_keys):
        group = groups[key]
        idx = gi if gi < len(group) else len(group) - 1
        representatives.append(group[idx])
    return representatives


# ── Instance parser ──────────────────────────────────────────────────────────


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
