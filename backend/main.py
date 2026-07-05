"""FastAPI server for CVRP solver with WebSocket real-time communication."""

import asyncio
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from cvrp.hga import HybridGeneticAlgorithm
from cvrp.instance import discover_instances, read_instance

app = FastAPI(title="CVRP Solver", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Available instances
INSTANCES_DIR = Path(__file__).parent.parent / "instances"

# WebSocket connections and cancellation events
active_connections: dict[str, WebSocket] = {}
cancel_events: dict[str, asyncio.Event] = {}
running_tasks: dict[str, asyncio.Task] = {}


def get_available_instances() -> list[dict[str, Any]]:
    """List all available instances grouped by set."""
    sets = {"A": [], "B": [], "E": [], "P": []}
    for vrp_file in sorted(INSTANCES_DIR.glob("*.vrp")):
        name = vrp_file.stem
        set_name = name[0]
        if set_name in sets:
            try:
                inst = read_instance(vrp_file)
                sets[set_name].append(
                    {
                        "name": name,
                        "dimension": inst.dimension,
                        "capacity": inst.capacity,
                        "num_vehicles": inst.num_vehicles,
                        "optimal": inst.optimal_value,
                    }
                )
            except Exception:
                pass
    return [{"set": k, "instances": v} for k, v in sets.items()]


@app.get("/api/instances")
async def list_instances():
    """List all available VRP instances."""
    return get_available_instances()


@app.get("/api/instance/{name}")
async def get_instance(name: str):
    """Get details of a specific instance."""
    filepath = INSTANCES_DIR / f"{name}.vrp"
    if not filepath.exists():
        return {"error": "Instance not found"}
    inst = read_instance(filepath)
    return {
        "name": inst.name,
        "dimension": inst.dimension,
        "capacity": inst.capacity,
        "num_vehicles": inst.num_vehicles,
        "optimal": inst.optimal_value,
        "coords": inst.node_coords,
        "demands": inst.demands,
        "depot": inst.depot,
    }


async def run_algorithm_with_callback(
    websocket: WebSocket,
    instance_name: str,
    max_fitness_evals: int = 350_000,
    runs: int = 5,
    hga_config: dict | None = None,
    cancel_event: asyncio.Event | None = None,
):
    """Run the HGA algorithm and stream progress via WebSocket."""
    filepath = INSTANCES_DIR / f"{instance_name}.vrp"
    if not filepath.exists():
        await websocket.send_json({"type": "error", "message": "Instance not found"})
        return

    instance = read_instance(filepath)

    # Track all run results
    all_run_costs: list[float] = []
    all_convergence: list[list[float]] = []
    all_gens_to_best: list[int] = []
    best_overall = float("inf")
    best_routes = None

    total_start = time.time()

    for run_idx in range(runs):
        # Check cancellation before each run
        if cancel_event and cancel_event.is_set():
            await websocket.send_json({"type": "experiment_cancelled", "completed_runs": run_idx})
            return

        await websocket.send_json(
            {
                "type": "run_start",
                "run": run_idx + 1,
                "total_runs": runs,
                "instance": instance_name,
            }
        )

        # Async queue for real-time progress
        progress_queue: asyncio.Queue[dict] = asyncio.Queue()
        stop_event = asyncio.Event()

        # Thread-safe: callback from worker thread puts to async queue
        loop = asyncio.get_event_loop()

        def callback(data: dict):
            loop.call_soon_threadsafe(progress_queue.put_nowait, data)

        # Task to drain queue and send via WebSocket
        async def drain_progress(current_run: int):
            while not stop_event.is_set():
                try:
                    msg = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    await websocket.send_json({"type": "progress", "run": current_run, **msg})
                except asyncio.TimeoutError:
                    continue

        drain_task = asyncio.create_task(drain_progress(run_idx + 1))

        try:
            cfg = hga_config or {}
            hga = HybridGeneticAlgorithm(
                instance=instance,
                population_size=cfg.get("population_size", 100),
                max_evaluations=max_fitness_evals,
                crossover_rate=cfg.get("crossover_rate", 0.8),
                mutation_rate=cfg.get("mutation_rate", 0.1),
                local_search_rate=cfg.get("local_search_rate", 0.1),
                tournament_size=cfg.get("tournament_size", 2),
                elite_count=cfg.get("elite_count", 2),
                local_search_max_iter=cfg.get("local_search_max_iter", 2),
                granular_size=cfg.get("granular_size", 15),
                callback=callback,
                cancel_check=cancel_event.is_set if cancel_event else None,
                seed=run_idx * 42 + 12345,
            )

            # Run in thread pool to avoid blocking
            def run_hga():
                return hga.run(track_convergence=True)

            solution = await asyncio.to_thread(run_hga)

            # Drain remaining messages
            await asyncio.sleep(0.2)
            while not progress_queue.empty():
                try:
                    msg = progress_queue.get_nowait()
                    await websocket.send_json({"type": "progress", "run": run_idx + 1, **msg})
                except asyncio.QueueEmpty:
                    break
        finally:
            stop_event.set()
            drain_task.cancel()
            try:
                await drain_task
            except asyncio.CancelledError:
                pass

        all_run_costs.append(solution.cost)
        all_convergence.append(hga.best_cost_history[:])
        all_gens_to_best.append(solution.generations_to_best)

        if solution.cost < best_overall:
            best_overall = solution.cost
            best_routes = solution.routes

        await websocket.send_json(
            {
                "type": "run_complete",
                "run": run_idx + 1,
                "cost": solution.cost,
                "routes": [[int(n) for n in r] for r in (solution.routes or [])],
                "generations_to_best": solution.generations_to_best,
                "num_vehicles": len(solution.routes),
                "evaluations": hga.evaluations,
            }
        )

    total_elapsed = time.time() - total_start

    # Compute statistics
    mean_cost = sum(all_run_costs) / len(all_run_costs)
    variance = sum((c - mean_cost) ** 2 for c in all_run_costs) / len(all_run_costs)
    std_dev = variance**0.5

    # Downsample convergence data for WebSocket transfer (max ~200 points per run)
    downsampled_conv = []
    for conv in all_convergence:
        if len(conv) <= 300:
            downsampled_conv.append(conv)
        else:
            step = len(conv) // 200
            downsampled_conv.append(conv[::step] + [conv[-1]])

    await websocket.send_json(
        {
            "type": "experiment_complete",
            "instance": instance_name,
            "optimal": instance.optimal_value,
            "best": min(all_run_costs),
            "mean": mean_cost,
            "std_dev": std_dev,
            "runs": all_run_costs,
            "generations_to_best": all_gens_to_best,
            "num_vehicles": [len(r) for r in (best_routes or [[]])],
            "routes": [[int(n) for n in r] for r in (best_routes or [])],
            "convergence": downsampled_conv,
            "execution_time": total_elapsed,
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time algorithm progress."""
    await websocket.accept()
    client_id = str(id(websocket))
    active_connections[client_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "run":
                # Cancel any previous run for this client
                if client_id in running_tasks and not running_tasks[client_id].done():
                    running_tasks[client_id].cancel()
                    if client_id in cancel_events:
                        cancel_events[client_id].set()

                discovered = discover_instances()
                instance_name = data.get("instance", discovered[0] if discovered else "A-n45-k7")
                max_evals = data.get("max_evals", 350_000)
                runs = data.get("runs", 5)
                hga_config = {
                    "population_size": data.get("population_size", 100),
                    "crossover_rate": data.get("crossover_rate", 0.8),
                    "mutation_rate": data.get("mutation_rate", 0.1),
                    "local_search_rate": data.get("local_search_rate", 0.1),
                    "tournament_size": data.get("tournament_size", 2),
                    "elite_count": data.get("elite_count", 2),
                    "local_search_max_iter": data.get("local_search_max_iter", 2),
                    "granular_size": data.get("granular_size", 15),
                }
                # Create a fresh cancel event for this run
                cancel_events[client_id] = asyncio.Event()
                task = asyncio.create_task(
                    run_algorithm_with_callback(
                        websocket,
                        instance_name,
                        max_evals,
                        runs,
                        hga_config,
                        cancel_events[client_id],
                    )
                )

                def _log_done(t: asyncio.Task) -> None:
                    exc = t.exception()
                    if exc:
                        print(f"[Task] Experiment task finished with error: {exc}")

                task.add_done_callback(_log_done)
                running_tasks[client_id] = task
            elif action == "stop":
                cancel_event = cancel_events.get(client_id)
                if cancel_event:
                    cancel_event.set()
            elif action == "list_instances":
                instances = get_available_instances()
                await websocket.send_json({"type": "instances", "data": instances})
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        # Set cancel event and cancel any running task for this client
        cancel_event = cancel_events.pop(client_id, None)
        if cancel_event:
            cancel_event.set()
        task = running_tasks.pop(client_id, None)
        if task and not task.done():
            task.cancel()
        active_connections.pop(client_id, None)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "instances": len(list(INSTANCES_DIR.glob("*.vrp")))}


def main():
    """Entry point for the server."""
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
