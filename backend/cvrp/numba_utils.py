"""Numba-accelerated functions for the HGA CVRP solver.

All functions in this module are JIT-compiled with @njit for maximum performance.
They operate on numpy arrays with primitive types (float64, int32).
"""

import numpy as np
from numba import njit


@njit(cache=True, nogil=True)
def route_cost_numba(
    route: np.ndarray, dist: np.ndarray, depot: int
) -> float:
    """Compute cost of a single route (array of customer indices)."""
    n = len(route)
    if n == 0:
        return 0.0
    cost = dist[depot, route[0]]
    for k in range(n - 1):
        cost += dist[route[k], route[k + 1]]
    cost += dist[route[n - 1], depot]
    return cost


@njit(cache=True, nogil=True)
def compute_cost_numba(
    routes_flat: np.ndarray,
    route_ends: np.ndarray,
    num_routes: int,
    dist: np.ndarray,
    depot: int,
) -> float:
    """Compute total cost from flat routes array.

    routes_flat: 1D int32 array with all customers in route order
    route_ends: 1D int32 array, route_ends[i] = end index (exclusive) of route i
    """
    total = 0.0
    start = 0
    for r in range(num_routes):
        end = route_ends[r]
        if end > start:
            total += dist[depot, routes_flat[start]]
            for k in range(start, end - 1):
                total += dist[routes_flat[k], routes_flat[k + 1]]
            total += dist[routes_flat[end - 1], depot]
        start = end
    return total


@njit(cache=True, nogil=True)
def split_numba(
    perm: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: int,
    depot: int,
) -> tuple:
    """Prins' split algorithm: optimally partition a permutation into feasible routes.

    Args:
        perm: 1D int32 array of customer indices
        dist: 2D float64 distance matrix
        demands: 1D int32 array of customer demands
        capacity: vehicle capacity
        depot: depot index

    Returns:
        (routes_flat, route_ends, num_routes, total_cost)
    """
    n = len(perm)

    # Precompute cumulative distance along permutation
    cum_dist = np.zeros(n + 1, dtype=np.float64)
    for i in range(1, n):
        cum_dist[i + 1] = cum_dist[i] + dist[perm[i - 1], perm[i]]

    # DP arrays
    INF = 1e100
    P = np.full(n + 1, INF, dtype=np.float64)
    P[0] = 0.0
    pred = np.full(n + 1, -1, dtype=np.int32)

    for i in range(1, n + 1):
        load = 0
        for j in range(i, 0, -1):
            load += demands[perm[j - 1]]
            if load > capacity:
                break

            # Cost of route from j to i
            route_len = (
                dist[depot, perm[j - 1]]
                + (cum_dist[i] - cum_dist[j])
                + dist[perm[i - 1], depot]
            )

            prev = P[j - 1]
            if prev + route_len < P[i]:
                P[i] = prev + route_len
                pred[i] = j - 1

    # Backtrack to build routes
    routes_flat = np.zeros(n, dtype=np.int32)
    route_ends = np.zeros(n, dtype=np.int32)
    num_routes = 0
    pos = 0

    # Build routes in reverse, then we'll reverse each route
    i = n
    while i > 0:
        j = pred[i] + 1
        # Copy segment perm[j-1 : i] into routes_flat
        for k in range(j - 1, i):
            routes_flat[pos] = perm[k]
            pos += 1
        route_ends[num_routes] = pos
        num_routes += 1
        i = j - 1

    # Reverse each route in the flat array (since we built them from end to start)
    start = 0
    for r in range(num_routes):
        end = route_ends[r]
        # Reverse segment [start, end)
        left = start
        right = end - 1
        while left < right:
            tmp = routes_flat[left]
            routes_flat[left] = routes_flat[right]
            routes_flat[right] = tmp
            left += 1
            right -= 1
        start = end

    total_cost = P[n]
    return routes_flat, route_ends, num_routes, total_cost


@njit(cache=True, nogil=True)
def two_opt_numba(
    route: np.ndarray, dist: np.ndarray, depot: int
) -> np.ndarray:
    """2-opt improvement for a single route (steepest descent)."""
    n = len(route)
    if n < 3:
        return route.copy()

    best = route.copy()
    best_cost = route_cost_numba(best, dist, depot)

    improved = True
    while improved:
        improved = False
        best_move_cost = best_cost
        best_i = -1
        best_j = -1

        # We try to reverse the segment best[i : j+1]
        for i in range(n - 1):
            for j in range(i + 1, n):
                if i == 0 and j == n - 1:
                    continue  # Reversing the whole route is equivalent for symmetric TSP

                # Compute the old and new costs at the boundaries of the segment best[i : j]
                if i == 0:
                    old_enter = dist[depot, best[0]]
                    new_enter = dist[depot, best[j]]
                else:
                    old_enter = dist[best[i - 1], best[i]]
                    new_enter = dist[best[i - 1], best[j]]

                if j == n - 1:
                    old_leave = dist[best[n - 1], depot]
                    new_leave = dist[best[i], depot]
                else:
                    old_leave = dist[best[j], best[j + 1]]
                    new_leave = dist[best[i], best[j + 1]]

                old_cost = old_enter + old_leave
                new_cost = new_enter + new_leave

                if new_cost < old_cost - 1e-10:
                    delta = old_cost - new_cost
                    if delta > 0:
                        candidate_cost = best_cost - delta
                        if candidate_cost < best_move_cost - 1e-10:
                            best_move_cost = candidate_cost
                            best_i = i
                            best_j = j

        if best_i >= 0:
            # Apply the best move: reverse segment [best_i, best_j]
            left = best_i
            right = best_j
            while left < right:
                tmp = best[left]
                best[left] = best[right]
                best[right] = tmp
                left += 1
                right -= 1
            best_cost = best_move_cost
            improved = True

    return best


@njit(cache=True, nogil=True)
def or_opt_numba(
    route: np.ndarray, dist: np.ndarray, depot: int
) -> np.ndarray:
    """Or-opt: relocate a segment of 1-3 consecutive nodes (steepest descent)."""
    n = len(route)
    if n < 3:
        return route.copy()

    best = route.copy()
    best_cost = route_cost_numba(best, dist, depot)

    improved = True
    while improved:
        improved = False
        best_move_cost = best_cost
        best_seg_len = -1
        best_seg_start = -1
        best_insert_pos = -1

        for seg_len in (1, 2, 3):
            if seg_len > n:
                continue
            for i in range(n - seg_len + 1):
                # Extract segment and compute remaining
                for j in range(n + 1):  # insertion position
                    if i <= j <= i + seg_len:
                        continue  # same position
                    if j < 0 or j > n:
                        continue

                    # Build new route: remaining (without segment) with segment inserted at j
                    new_cost = _or_opt_delta(
                        best, dist, depot, n, i, seg_len, j
                    )
                    if new_cost < best_move_cost - 1e-10:
                        best_move_cost = new_cost
                        best_seg_len = seg_len
                        best_seg_start = i
                        best_insert_pos = j

        if best_seg_len >= 0:
            # Apply best move
            best = _apply_or_opt(best, best_seg_start, best_seg_len, best_insert_pos)
            best_cost = best_move_cost
            improved = True

    return best


@njit(cache=True, nogil=True)
def _or_opt_delta(
    route: np.ndarray,
    dist: np.ndarray,
    depot: int,
    n: int,
    seg_start: int,
    seg_len: int,
    insert_pos: int,
) -> float:
    """Compute cost after Or-opt move without building the full route.

    Instead of building an entirely new route, we compute the delta.
    """
    # If segment is being moved to right (insert_pos > seg_start + seg_len)
    # or left (insert_pos < seg_start), the connections change.
    # We compute by building the route inline - it's simpler and fast with numba.
    new_route = np.empty(n, dtype=np.int32)
    idx = 0

    # Copy elements before the earlier position
    if insert_pos < seg_start:
        # Insert segment first
        early_end = insert_pos
        for k in range(early_end):
            new_route[idx] = route[k]
            idx += 1
        # Insert segment
        for k in range(seg_len):
            new_route[idx] = route[seg_start + k]
            idx += 1
        # Copy between insert_pos and seg_start
        for k in range(early_end, seg_start):
            new_route[idx] = route[k]
            idx += 1
        # Copy after segment
        for k in range(seg_start + seg_len, n):
            new_route[idx] = route[k]
            idx += 1
    else:
        # Segment comes first
        # Copy before segment
        for k in range(seg_start):
            new_route[idx] = route[k]
            idx += 1
        # Copy between segment and insert_pos
        after_seg = seg_start + seg_len
        for k in range(after_seg, insert_pos):
            new_route[idx] = route[k]
            idx += 1
        # Insert segment
        for k in range(seg_len):
            new_route[idx] = route[seg_start + k]
            idx += 1
        # Copy after insert_pos
        for k in range(insert_pos, n):
            new_route[idx] = route[k]
            idx += 1

    return route_cost_numba(new_route, dist, depot)


@njit(cache=True, nogil=True)
def _apply_or_opt(
    route: np.ndarray, seg_start: int, seg_len: int, insert_pos: int
) -> np.ndarray:
    """Apply Or-opt move and return new route."""
    n = len(route)
    new_route = np.empty(n, dtype=np.int32)
    idx = 0

    if insert_pos < seg_start:
        for k in range(insert_pos):
            new_route[idx] = route[k]
            idx += 1
        for k in range(seg_len):
            new_route[idx] = route[seg_start + k]
            idx += 1
        for k in range(insert_pos, seg_start):
            new_route[idx] = route[k]
            idx += 1
        for k in range(seg_start + seg_len, n):
            new_route[idx] = route[k]
            idx += 1
    else:
        for k in range(seg_start):
            new_route[idx] = route[k]
            idx += 1
        after_seg = seg_start + seg_len
        for k in range(after_seg, insert_pos):
            new_route[idx] = route[k]
            idx += 1
        for k in range(seg_len):
            new_route[idx] = route[seg_start + k]
            idx += 1
        for k in range(insert_pos, n):
            new_route[idx] = route[k]
            idx += 1

    return new_route


@njit(cache=True, nogil=True)
def order_crossover_numba(
    p1: np.ndarray, p2: np.ndarray, cx1: int, cx2: int
) -> np.ndarray:
    n = len(p1)
    child = np.full(n, -1, dtype=np.int32)
    child[cx1 : cx2 + 1] = p1[cx1 : cx2 + 1]

    # Use a boolean mask of size n + 1 for fast O(1) JIT set lookups
    inherited = np.zeros(n + 1, dtype=np.bool_)
    for k in range(cx1, cx2 + 1):
        inherited[p1[k]] = True

    idx = (cx2 + 1) % n
    p2_idx = (cx2 + 1) % n

    for _ in range(n - (cx2 - cx1 + 1)):
        while inherited[p2[p2_idx]]:
            p2_idx = (p2_idx + 1) % n
        val = p2[p2_idx]
        child[idx] = val
        inherited[val] = True
        idx = (idx + 1) % n
        p2_idx = (p2_idx + 1) % n

    return child
