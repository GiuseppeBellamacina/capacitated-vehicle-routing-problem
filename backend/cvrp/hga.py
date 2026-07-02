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

        # Stats
        self.evaluations: int = 0
        self.generation: int = 0
        self.best_solution: Solution | None = None
        self.best_cost_history: list[float] = []

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
        """Tournament selection: pick best of k random individuals."""
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

        # Select two crossover points
        cx1, cx2 = sorted(random.sample(range(n), 2))

        # Child inherits segment from parent1
        child = [-1] * n
        child[cx1 : cx2 + 1] = p1[cx1 : cx2 + 1]

        # Fill remaining positions with genes from parent2 in order
        inherited = set(child[cx1 : cx2 + 1])
        idx = (cx2 + 1) % n
        p2_idx = (cx2 + 1) % n

        for _ in range(n - (cx2 - cx1 + 1)):
            while p2[p2_idx] in inherited:
                p2_idx = (p2_idx + 1) % n
            child[idx] = p2[p2_idx]
            inherited.add(p2[p2_idx])
            idx = (idx + 1) % n
            p2_idx = (p2_idx + 1) % n

        return child

    # --- Mutation Operators ---

    def swap_mutation(self, perm: list[int]) -> list[int]:
        """Swap two random positions."""
        if len(perm) < 2:
            return perm
        i, j = random.sample(range(len(perm)), 2)
        perm = perm[:]
        perm[i], perm[j] = perm[j], perm[i]
        return perm

    def insert_mutation(self, perm: list[int]) -> list[int]:
        """Remove element at i and insert at j."""
        if len(perm) < 2:
            return perm
        i = random.randrange(len(perm))
        j = random.randrange(len(perm))
        perm = perm[:]
        val = perm.pop(i)
        perm.insert(j, val)
        return perm

    def inversion_mutation(self, perm: list[int]) -> list[int]:
        """Reverse a subsequence."""
        if len(perm) < 2:
            return perm
        i, j = sorted(random.sample(range(len(perm)), 2))
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
        """Inter-route relocate: move a customer from one route to another (steepest descent)."""
        if len(routes) < 2:
            return routes

        best = [r[:] for r in routes]
        best_cost = self._compute_cost(best)
        improved = True
        max_iter = self.local_search_max_iter
        iter_count = 0

        while improved and iter_count < max_iter:
            iter_count += 1
            improved = False
            best_move: list[list[int]] | None = None
            best_move_cost = best_cost

            for ri, route_from in enumerate(best):
                if len(route_from) < 1:
                    continue
                for fi, node in enumerate(route_from):
                    demand = self.demands[node]
                    for rj, route_to in enumerate(best):
                        if ri == rj:
                            continue
                        if route_demand(route_to, self.demands) + demand > self.capacity:
                            continue
                        
                        # Compute base cost of these two routes before modification
                        cost_before = self._route_cost(route_from) + self._route_cost(route_to)
                        
                        # In-place modification: move node from route_from to route_to
                        route_from.pop(fi)
                        cost_from_after = self._route_cost(route_from)
                        
                        for pos in range(len(route_to) + 1):
                            route_to.insert(pos, node)
                            cost_to_after = self._route_cost(route_to)
                            
                            delta = (cost_from_after + cost_to_after) - cost_before
                            new_cost = best_cost + delta
                            
                            if new_cost < best_move_cost - 1e-8:
                                best_move_cost = new_cost
                                best_move = [r[:] for r in best]
                            route_to.pop(pos)
                        route_from.insert(fi, node)  # Restore original state

            if best_move is not None:
                best = best_move
                best_cost = best_move_cost
                improved = True

        return best

    def _exchange(self, routes: list[list[int]]) -> list[list[int]]:
        """Inter-route exchange: swap two customers between routes (steepest descent)."""
        if len(routes) < 2:
            return routes

        best = [r[:] for r in routes]
        best_cost = self._compute_cost(best)
        improved = True
        max_iter = self.local_search_max_iter
        iter_count = 0

        while improved and iter_count < max_iter:
            iter_count += 1
            improved = False
            best_move: list[list[int]] | None = None
            best_move_cost = best_cost

            for ri, route_a in enumerate(best):
                for rj, route_b in enumerate(best):
                    if ri >= rj:
                        continue
                    for ai, node_a in enumerate(route_a):
                        for bj, node_b in enumerate(route_b):
                            dem_a = self.demands[node_a]
                            dem_b = self.demands[node_b]
                            load_a = route_demand(route_a, self.demands) - dem_a + dem_b
                            load_b = route_demand(route_b, self.demands) - dem_b + dem_a
                            if load_a > self.capacity or load_b > self.capacity:
                                continue
                            
                            # Compute base cost of these two routes before swap
                            cost_before = self._route_cost(route_a) + self._route_cost(route_b)
                            
                            # In-place swap
                            route_a[ai] = node_b
                            route_b[bj] = node_a
                            cost_after = self._route_cost(route_a) + self._route_cost(route_b)
                            
                            delta = cost_after - cost_before
                            new_cost = best_cost + delta
                            
                            if new_cost < best_move_cost - 1e-8:
                                best_move_cost = new_cost
                                best_move = [r[:] for r in best]
                            # Restore swap
                            route_a[ai] = node_a
                            route_b[bj] = node_b

            if best_move is not None:
                best = best_move
                best_cost = best_move_cost
                improved = True

        return best

    def local_search(self, solution: Solution) -> Solution:
        """Apply local search to improve a solution."""
        routes = [r[:] for r in solution.routes]

        # 1. Intra-route: 2-opt
        for i in range(len(routes)):
            routes[i] = self._two_opt(routes[i])

        # 2. Intra-route: Or-opt
        for i in range(len(routes)):
            routes[i] = self._or_opt(routes[i])

        # 3. Inter-route: relocate
        routes = self._relocate(routes)

        # 4. Inter-route: exchange
        routes = self._exchange(routes)

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

                # Local search
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
