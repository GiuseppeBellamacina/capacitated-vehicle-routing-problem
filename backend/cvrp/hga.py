"""Hybrid Genetic Algorithm for CVRP.

Implements a permutation-based GA with:
- Prins' split algorithm for route partitioning
- Order Crossover (OX)
- Multiple mutation operators (swap, insert, inversion)
- Local search (2-opt, Or-opt, relocate, exchange)
- Tournament selection with elitism
"""

import random
import time
import numpy as np
from dataclasses import dataclass
from typing import Callable

from .instance import CVRPInstance, compute_distance_matrix
from .utils import route_demand
from .numba_utils import (
    split_numba,
    two_opt_numba,
    or_opt_numba,
    order_crossover_numba,
)


@dataclass
class Solution:
    """Represents a CVRP solution."""

    routes: list[list[int]]
    cost: float
    feasible: bool = True
    generations_to_best: int = 0


@dataclass
class ExperimentResult:
    """Results from a single experiment run."""

    instance_name: str
    best_cost: float
    all_run_costs: list[float]
    convergence_data: list[list[float]]  # per-run convergence
    generations_to_best: list[int]
    execution_time: float
    num_vehicles_used: list[int]
    routes: list[list[int]] | None = None


class HybridGeneticAlgorithm:
    """Hybrid Genetic Algorithm for the Capacitated Vehicle Routing Problem."""

    def __init__(
        self,
        instance: CVRPInstance,
        population_size: int = 100,
        max_evaluations: int = 350_000,
        tournament_size: int = 2,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.1,
        local_search_rate: float = 0.1,
        elite_count: int = 2,
        local_search_max_iter: int = 2,
        granular_size: int = 15,
        seed: int | None = None,
        callback: Callable[[dict], None] | None = None,
    ):
        self.instance = instance
        self.population_size = population_size
        self.max_evaluations = max_evaluations
        self.tournament_size = tournament_size
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.local_search_rate = local_search_rate
        self.elite_count = elite_count
        self.local_search_max_iter = local_search_max_iter
        self.granular_size = granular_size
        self.use_granular_search = (granular_size > 0)
        self.callback = callback

        if seed is not None:
            random.seed(seed)

        self.dist_matrix = compute_distance_matrix(instance)
        self.demands = np.array(instance.demands, dtype=np.int32)
        self.capacity = instance.capacity
        self.num_customers = instance.num_customers
        self.num_vehicles = instance.num_vehicles
        self.depot = instance.depot

        # Customer indices (1-indexed, excluding depot at 0)
        self.customers = list(range(1, self.num_customers + 1))

        # Build granular neighborhood for each customer
        self.granular_neighbors = self._build_granular_neighborhoods()

        # Stats
        self.evaluations: int = 0
        self.generation: int = 0
        self.best_solution: Solution | None = None
        self.best_cost_history: list[float] = []

    def _build_granular_neighborhoods(self) -> dict[int, set[int]]:
        """For each customer, build a set of its granular_size nearest neighbors."""
        neighborhoods = {}
        if not self.use_granular_search:
            return neighborhoods
        for i in self.customers:
            # Sort other customers by distance
            sorted_neighbors = sorted(
                self.customers,
                key=lambda j: self.dist_matrix[i][j]
            )
            # Filter out self
            sorted_neighbors = [j for j in sorted_neighbors if j != i]
            # Take the top granular_size neighbors
            neighborhoods[i] = set(sorted_neighbors[:self.granular_size])
        return neighborhoods

    # --- Split Algorithm (Prins, 2004) ---

    def split(self, permutation: list[int]) -> Solution:
        """
        Optimal splitting of a permutation into feasible routes.
        Uses DP with numba acceleration.
        """
        n = len(permutation)
        if n == 0:
            return Solution(routes=[], cost=0.0)

        perm_np = np.array(permutation, dtype=np.int32)

        routes_flat, route_ends, num_routes, cost = split_numba(
            perm_np, self.dist_matrix, self.demands, self.capacity, self.depot
        )

        # If DP returned no feasible split, fall back to greedy
        if num_routes == 0 or cost > 1e50:
            return self._greedy_split(permutation)

        # Convert flat arrays back to list[list[int]]
        routes = []
        start = 0
        for r in range(num_routes):
            end = route_ends[r]
            routes.append(routes_flat[start:end].tolist())
            start = end

        self.evaluations += 1
        return Solution(routes=routes, cost=cost)

    def _greedy_split(self, permutation: list[int]) -> Solution:
        """Greedy split as fallback when DP split is infeasible."""
        routes: list[list[int]] = []
        current_route: list[int] = []
        current_load: int = 0

        for node in permutation:
            demand = self.demands[node]
            if current_load + demand <= self.capacity:
                current_route.append(node)
                current_load += demand
            else:
                if current_route:
                    routes.append(current_route)
                current_route = [node]
                current_load = demand

        if current_route:
            routes.append(current_route)

        # If more routes than vehicles, redistribute excess customers
        if len(routes) > self.num_vehicles:
            # Sort routes by load (ascending) and merge small routes into larger ones where possible
            routes.sort(key=lambda r: route_demand(r, self.demands))
            while len(routes) > self.num_vehicles:
                # Take smallest route and try to redistribute its customers
                smallest = routes.pop(0)
                for node in smallest:
                    placed = False
                    for route in routes:
                        if route_demand(route, self.demands) + self.demands[node] <= self.capacity:
                            route.append(node)
                            placed = True
                            break
                    if not placed:
                        # Force into route with most remaining capacity (slightly infeasible)
                        best_route = min(routes, key=lambda r: route_demand(r, self.demands))
                        best_route.append(node)

        cost = self._compute_cost(routes)
        self.evaluations += 1
        return Solution(routes=routes, cost=cost, feasible=len(routes) <= self.num_vehicles)

    def _compute_cost(self, routes: list[list[int]]) -> float:
        """Compute total cost of a solution (inline, fast path for relocate/exchange)."""
        total = 0.0
        dm = self.dist_matrix
        depot = self.depot
        for route in routes:
            if not route:
                continue
            total += dm[depot, route[0]]
            for k in range(len(route) - 1):
                total += dm[route[k], route[k + 1]]
            total += dm[route[-1], depot]
        return total

    # --- Initialization ---

    def _nearest_neighbor_heuristic(self) -> list[int]:
        """Generate a permutation using nearest neighbor heuristic."""
        unvisited = set(self.customers)
        current = self.depot
        perm = []

        while unvisited:
            best = None
            best_dist = float("inf")
            for node in unvisited:
                d = self.dist_matrix[current][node]
                if d < best_dist:
                    best_dist = d
                    best = node
            if best is None:
                break
            perm.append(best)
            unvisited.remove(best)
            current = best

        return perm

    def _savings_heuristic(self) -> list[int]:
        """Generate a permutation using Clarke-Wright savings heuristic."""
        # Compute savings: s(i,j) = d(0,i) + d(0,j) - d(i,j)
        savings = []
        for i in self.customers:
            for j in self.customers:
                if i < j:
                    s = (
                        self.dist_matrix[self.depot][i]
                        + self.dist_matrix[self.depot][j]
                        - self.dist_matrix[i][j]
                    )
                    savings.append((s, i, j))

        savings.sort(key=lambda x: x[0], reverse=True)

        # Build routes greedily
        routes: list[list[int]] = []
        in_route = set()

        for s, i, j in savings:
            if i in in_route or j in in_route:
                continue
            # Try to start a new route
            demand = self.demands[i] + self.demands[j]
            if demand <= self.capacity:
                routes.append([i, j])
                in_route.add(i)
                in_route.add(j)

        # Add remaining customers
        remaining = [c for c in self.customers if c not in in_route]
        for c in remaining:
            routes.append([c])

        # Flatten routes into a permutation
        perm = []
        for route in routes:
            perm.extend(route)
        return perm

    def _random_permutation(self) -> list[int]:
        """Generate a random permutation of customers."""
        perm = self.customers[:]
        random.shuffle(perm)
        return perm

    def create_initial_population(self) -> list[Solution]:
        """Create initial population using heuristics and random permutations."""
        population: list[Solution] = []

        # Add heuristic-based solutions
        print("    [HGA Init] Generating Nearest Neighbor solution...")
        nn_perm = self._nearest_neighbor_heuristic()
        population.append(self.split(nn_perm))

        print("    [HGA Init] Generating Savings Heuristic solution...")
        savings_perm = self._savings_heuristic()
        population.append(self.split(savings_perm))

        # Add random permutations
        print(f"    [HGA Init] Generating remaining {self.population_size - len(population)} random solutions...")
        while len(population) < self.population_size:
            perm = self._random_permutation()
            population.append(self.split(perm))

        # Sort by cost
        population.sort(key=lambda s: s.cost)
        print("    [HGA Init] Initial population completed.")
        return population

    # --- Selection ---

    def tournament_select(self, population: list[Solution]) -> Solution:
        """Tournament selection: pick best of k random individuals (optimized for k=2)."""
        if self.tournament_size == 2:
            n = len(population)
            s1 = population[random.randrange(n)]
            s2 = population[random.randrange(n)]
            return s1 if s1.cost < s2.cost else s2
        candidates = random.sample(population, self.tournament_size)
        return min(candidates, key=lambda s: s.cost)

    # --- Crossover: Order Crossover (OX) ---

    def order_crossover(
        self, parent1: Solution, parent2: Solution
    ) -> list[int]:
        """Order Crossover: preserves relative order from both parents."""
        # Extract permutations from solutions
        p1 = []
        for route in parent1.routes:
            p1.extend(route)
        p2 = []
        for route in parent2.routes:
            p2.extend(route)

        n = len(p1)
        if n < 2:
            return p1[:] if p1 else p2[:]

        # Fast O(1) sampling of two unique indices
        cx1 = random.randrange(n)
        cx2 = random.randrange(n - 1)
        if cx2 >= cx1:
            cx2 += 1
        else:
            cx1, cx2 = cx2, cx1

        # Convert to numpy arrays and call JIT crossover
        p1_np = np.array(p1, dtype=np.int32)
        p2_np = np.array(p2, dtype=np.int32)
        child_np = order_crossover_numba(p1_np, p2_np, cx1, cx2)

        return child_np.tolist()

    # --- Mutation Operators ---

    def swap_mutation(self, perm: list[int]) -> list[int]:
        """Swap two random positions (optimized index selection)."""
        n = len(perm)
        if n < 2:
            return perm
        i = random.randrange(n)
        j = random.randrange(n - 1)
        if j >= i:
            j += 1
        perm = perm[:]
        perm[i], perm[j] = perm[j], perm[i]
        return perm

    def insert_mutation(self, perm: list[int]) -> list[int]:
        """Remove element at i and insert at j."""
        n = len(perm)
        if n < 2:
            return perm
        i = random.randrange(n)
        j = random.randrange(n)
        perm = perm[:]
        val = perm.pop(i)
        perm.insert(j, val)
        return perm

    def inversion_mutation(self, perm: list[int]) -> list[int]:
        """Reverse a subsequence (optimized index selection)."""
        n = len(perm)
        if n < 2:
            return perm
        i = random.randrange(n)
        j = random.randrange(n - 1)
        if j >= i:
            j += 1
        else:
            i, j = j, i
        perm = perm[:]
        perm[i : j + 1] = reversed(perm[i : j + 1])
        return perm

    def mutate(self, perm: list[int]) -> list[int]:
        """Apply a random mutation operator."""
        r = random.random()
        if r < 0.4:
            return self.swap_mutation(perm)
        elif r < 0.7:
            return self.insert_mutation(perm)
        else:
            return self.inversion_mutation(perm)

    # --- Local Search Operators ---

    def _two_opt(self, route: list[int]) -> list[int]:
        """2-opt improvement for a single route (numba-accelerated)."""
        if len(route) < 3:
            return route
        route_np = np.array(route, dtype=np.int32)
        result = two_opt_numba(route_np, self.dist_matrix, self.depot)
        return result.tolist()

    def _route_cost(self, route: list[int]) -> float:
        """Compute cost of a single route (inline, fast path for or_opt)."""
        if not route:
            return 0.0
        dm = self.dist_matrix
        depot = self.depot
        cost = dm[depot, route[0]]
        for k in range(len(route) - 1):
            cost += dm[route[k], route[k + 1]]
        cost += dm[route[-1], depot]
        return cost

    def _or_opt(self, route: list[int]) -> list[int]:
        """Or-opt: relocate a segment of 1-3 consecutive nodes (numba-accelerated)."""
        if len(route) < 3:
            return route
        route_np = np.array(route, dtype=np.int32)
        result = or_opt_numba(route_np, self.dist_matrix, self.depot)
        return result.tolist()

    def _relocate(self, routes: list[list[int]]) -> list[list[int]]:
        """Inter-route relocate: move a customer from one route to another (steepest descent).
        Uses pre-computed route loads and index-only move tracking to avoid O(n) route_demand
        calls and deep copies in the inner loop."""
        if len(routes) < 2:
            return routes

        best = [r[:] for r in routes]
        best_cost = self._compute_cost(best)
        improved = True
        max_iter = self.local_search_max_iter
        iter_count = 0
        depot = self.depot
        dm = self.dist_matrix
        demands = self.demands

        # Pre-compute route loads once — O(total_customers) instead of O(n) per inner iteration
        route_loads = [sum(demands[n] for n in r) for r in best]

        while improved and (max_iter <= 0 or iter_count < max_iter):
            iter_count += 1
            improved = False
            best_move_cost = best_cost
            best_move_info = None  # (ri, fi, rj, pos) — no deep copies

            for ri, route_from in enumerate(best):
                if len(route_from) < 1:
                    continue
                for fi, node in enumerate(route_from):
                    demand = demands[node]

                    # O(1) delta on route_from by removing 'node'
                    prev_from = route_from[fi - 1] if fi > 0 else depot
                    next_from = route_from[fi + 1] if fi < len(route_from) - 1 else depot
                    if len(route_from) == 1:
                        delta_from = -(dm[depot, node] + dm[node, depot])
                    else:
                        delta_from = dm[prev_from, next_from] - (dm[prev_from, node] + dm[node, next_from])

                    for rj, route_to in enumerate(best):
                        if ri == rj:
                            continue
                        # O(1) capacity check using pre-computed loads
                        if route_loads[rj] + demand > self.capacity:
                            continue

                        for pos in range(len(route_to) + 1):
                            # Granular search filter
                            if self.use_granular_search:
                                pn = route_to[pos - 1] if pos > 0 else 0
                                nn = route_to[pos] if pos < len(route_to) else 0
                                if (pn != 0 and pn not in self.granular_neighbors[node]) and \
                                   (nn != 0 and nn not in self.granular_neighbors[node]):
                                    continue

                            # O(1) delta on route_to by inserting 'node'
                            prev_node = route_to[pos - 1] if pos > 0 else depot
                            next_node = route_to[pos] if pos < len(route_to) else depot
                            delta_to = dm[prev_node, node] + dm[node, next_node] - dm[prev_node, next_node]

                            new_cost = best_cost + delta_from + delta_to

                            if new_cost < best_move_cost - 1e-8:
                                best_move_cost = new_cost
                                best_move_info = (ri, fi, rj, pos)

            if best_move_info is not None:
                ri, fi, rj, pos = best_move_info
                node = best[ri].pop(fi)
                # Adjust insertion index if moving within later route
                best[rj].insert(pos, node)
                route_loads[ri] -= demands[node]
                route_loads[rj] += demands[node]
                best_cost = best_move_cost
                improved = True

        return best

    def _exchange(self, routes: list[list[int]]) -> list[list[int]]:
        """Inter-route exchange: swap two customers between routes (steepest descent).
        Uses pre-computed route loads and index-only move tracking."""
        if len(routes) < 2:
            return routes

        best = [r[:] for r in routes]
        best_cost = self._compute_cost(best)
        improved = True
        max_iter = self.local_search_max_iter
        iter_count = 0
        depot = self.depot
        dm = self.dist_matrix
        demands = self.demands

        # Pre-compute route loads once
        route_loads = [sum(demands[n] for n in r) for r in best]

        while improved and (max_iter <= 0 or iter_count < max_iter):
            iter_count += 1
            improved = False
            best_move_cost = best_cost
            best_move_info = None  # (ri, ai, rj, bj) — no deep copies

            for ri, route_a in enumerate(best):
                for rj, route_b in enumerate(best):
                    if ri >= rj:
                        continue
                    for ai, node_a in enumerate(route_a):
                        dem_a = demands[node_a]
                        for bj, node_b in enumerate(route_b):
                            # Granular search filter
                            if self.use_granular_search:
                                if node_b not in self.granular_neighbors[node_a] and \
                                   node_a not in self.granular_neighbors[node_b]:
                                    continue

                            dem_b = demands[node_b]
                            # O(1) capacity check using pre-computed loads
                            if route_loads[ri] - dem_a + dem_b > self.capacity or \
                               route_loads[rj] - dem_b + dem_a > self.capacity:
                                continue

                            # O(1) delta computation for swap
                            prev_a = route_a[ai - 1] if ai > 0 else depot
                            next_a = route_a[ai + 1] if ai < len(route_a) - 1 else depot
                            delta_a = (dm[prev_a, node_b] + dm[node_b, next_a]) - \
                                      (dm[prev_a, node_a] + dm[node_a, next_a])

                            prev_b = route_b[bj - 1] if bj > 0 else depot
                            next_b = route_b[bj + 1] if bj < len(route_b) - 1 else depot
                            delta_b = (dm[prev_b, node_a] + dm[node_a, next_b]) - \
                                      (dm[prev_b, node_b] + dm[node_b, next_b])

                            new_cost = best_cost + delta_a + delta_b

                            if new_cost < best_move_cost - 1e-8:
                                best_move_cost = new_cost
                                best_move_info = (ri, ai, rj, bj)

            if best_move_info is not None:
                ri, ai, rj, bj = best_move_info
                node_a = best[ri][ai]
                node_b = best[rj][bj]
                best[ri][ai] = node_b
                best[rj][bj] = node_a
                route_loads[ri] += demands[node_b] - demands[node_a]
                route_loads[rj] += demands[node_a] - demands[node_b]
                best_cost = best_move_cost
                improved = True

        return best

    def _educate_light(self, solution: Solution) -> Solution:
        """Light education: apply fast JIT-compiled intra-route operators (2-opt) to all routes."""
        routes = [r[:] for r in solution.routes]
        for i in range(len(routes)):
            routes[i] = self._two_opt(routes[i])
        cost = self._compute_cost(routes)
        self.evaluations += 1
        return Solution(routes=routes, cost=cost)

    def local_search(self, solution: Solution) -> Solution:
        """Full local search: intra-route (2-opt + Or-opt) + inter-route (relocate + exchange).
        Inter-route operator order is randomized to avoid systematic bias."""
        routes = [r[:] for r in solution.routes]

        # Intra-route: 2-opt + Or-opt (always in this order, both JIT-compiled)
        for i in range(len(routes)):
            routes[i] = self._two_opt(routes[i])
        for i in range(len(routes)):
            routes[i] = self._or_opt(routes[i])

        # Inter-route: randomize operator order to avoid bias
        if random.random() < 0.5:
            routes = self._relocate(routes)
            routes = self._exchange(routes)
        else:
            routes = self._exchange(routes)
            routes = self._relocate(routes)

        # Remove empty routes
        routes = [r for r in routes if r]

        cost = self._compute_cost(routes)
        self.evaluations += 1
        # Count as 5 evaluations since local search is expensive
        self.evaluations += 4

        return Solution(routes=routes, cost=cost)

    # --- Main Evolution Loop ---

    def run(
        self,
        track_convergence: bool = True,
        convergence_interval: int = 5000,
    ) -> Solution:
        """Run the HGA algorithm. Returns the best solution found."""
        print("  [HGA Run] Initializing population...")
        population = self.create_initial_population()
        self.best_solution = min(population, key=lambda s: s.cost)
        best_gen = 0
        self.generation = 0

        print(f"  [HGA Run] Population initialized. Best initial cost: {self.best_solution.cost:.2f}")

        # Dynamically scale convergence interval to record around 100 points
        if convergence_interval == 5000:
            convergence_interval = max(1, self.max_evaluations // 100)

        if track_convergence:
            self.best_cost_history.append(self.best_solution.cost)

        last_recorded_evals = 0
        last_callback_time = 0.0
        print("  [HGA Run] Starting evolution loop...")

        from tqdm import tqdm
        pbar = tqdm(total=self.max_evaluations, desc="  Evolution", leave=False, initial=self.evaluations)

        while self.evaluations < self.max_evaluations:
            pbar.n = self.evaluations
            pbar.set_postfix(best=f"{self.best_solution.cost:.2f}")
            pbar.refresh()
            self.generation += 1
            new_population: list[Solution] = []

            # Elitism: keep best individuals
            population.sort(key=lambda s: s.cost)
            elites = population[: self.elite_count]
            new_population.extend(elites)

            # Generate offspring
            while len(new_population) < self.population_size:
                if random.random() < self.crossover_rate:
                    parent1 = self.tournament_select(population)
                    parent2 = self.tournament_select(population)
                    child_perm = self.order_crossover(parent1, parent2)
                else:
                    parent = self.tournament_select(population)
                    child_perm = []
                    for route in parent.routes:
                        child_perm.extend(route)

                # Mutation
                if random.random() < self.mutation_rate:
                    child_perm = self.mutate(child_perm)

                child = self.split(child_perm)

                # Light education: 2-opt on ALL children (fast, JIT-compiled)
                child = self._educate_light(child)

                # Full local search (inter-route) only at configured rate
                if random.random() < self.local_search_rate:
                    child = self.local_search(child)

                new_population.append(child)

                # Track best solution and convergence in real-time
                if child.cost < self.best_solution.cost - 1e-8:
                    self.best_solution = child
                    best_gen = self.generation

                if track_convergence and self.evaluations - last_recorded_evals >= convergence_interval:
                    self.best_cost_history.append(self.best_solution.cost)
                    last_recorded_evals = self.evaluations

            # Survivor selection: detect and replace duplicates to maintain diversity
            seen_costs: set[int] = set()
            for idx in range(len(new_population)):
                cost_key = int(new_population[idx].cost * 1000)  # 3 decimal places
                if cost_key in seen_costs:
                    # Replace duplicate with a fresh random individual
                    fresh_perm = self._random_permutation()
                    fresh = self.split(fresh_perm)
                    fresh = self._educate_light(fresh)
                    new_population[idx] = fresh
                    cost_key = int(fresh.cost * 1000)
                seen_costs.add(cost_key)

            population = new_population

            # WebSocket callback with time-based throttling (max 10Hz) and instant updates on improvement
            now = time.time()
            is_new_best = (best_gen == self.generation)
            if self.callback and (is_new_best or (now - last_callback_time >= 0.1) or self.evaluations >= self.max_evaluations):
                self.callback({
                    "generation": self.generation,
                    "evaluations": self.evaluations,
                    "best_cost": self.best_solution.cost,
                    "population_avg": sum(s.cost for s in population) / len(population),
                    "population_size": len(population),
                    "routes": [[int(n) for n in r] for r in (self.best_solution.routes or [])],
                })
                last_callback_time = now

            if self.evaluations >= self.max_evaluations:
                break

        self.best_solution.generations_to_best = best_gen

        if track_convergence:
            self.best_cost_history.append(self.best_solution.cost)

        pbar.close()
        return self.best_solution

    def run_experiment(
        self, runs: int = 5, track_convergence: bool = True
    ) -> ExperimentResult:
        """Run multiple independent runs and collect statistics."""
        all_costs = []
        all_convergence = []
        all_gens_to_best = []
        all_vehicles = []
        best_routes = None

        start_time = time.time()

        for run_idx in range(runs):
            # Reset state
            self.evaluations = 0
            self.generation = 0
            self.best_solution = None
            self.best_cost_history = []

            # Set different seed for each run
            random.seed(run_idx * 42 + 12345)

            solution = self.run(track_convergence=track_convergence)

            all_costs.append(solution.cost)
            all_convergence.append(self.best_cost_history[:])
            all_gens_to_best.append(solution.generations_to_best)
            all_vehicles.append(len(solution.routes))

            if best_routes is None or solution.cost < min(all_costs):
                best_routes = solution.routes

        elapsed = time.time() - start_time

        return ExperimentResult(
            instance_name=self.instance.name,
            best_cost=min(all_costs),
            all_run_costs=all_costs,
            convergence_data=all_convergence,
            generations_to_best=all_gens_to_best,
            execution_time=elapsed,
            num_vehicles_used=all_vehicles,
            routes=best_routes,
        )
