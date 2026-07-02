import React, { useState, useRef, useCallback, useEffect } from "react";

// --- Types ---

interface InstanceInfo {
  name: string;
  dimension: number;
  capacity: number;
  num_vehicles: number;
  optimal: number | null;
}

interface InstanceSet {
  set: string;
  instances: InstanceInfo[];
}

interface Coord {
  x: number;
  y: number;
}

interface WsProgress {
  type: "progress";
  run: number;
  generation: number;
  evaluations: number;
  best_cost: number;
  population_avg: number;
  routes?: number[][];
}

interface WsRunStart {
  type: "run_start";
  run: number;
  total_runs: number;
  instance: string;
}

interface WsRunComplete {
  type: "run_complete";
  run: number;
  cost: number;
  routes: number[][];
  generations_to_best: number;
  num_vehicles: number;
  evaluations: number;
}

interface WsExperimentComplete {
  type: "experiment_complete";
  instance: string;
  optimal: number | null;
  best: number;
  mean: number;
  std_dev: number;
  runs: number[];
  routes: number[][];
  convergence: number[][];
  execution_time: number;
  generations_to_best: number[];
}

type WsMessage =
  | WsProgress
  | WsRunStart
  | WsRunComplete
  | WsExperimentComplete
  | { type: "instances"; data: InstanceSet[] }
  | { type: "error"; message: string }
  | { type: "pong" };

// --- Route Canvas Component ---

interface RouteCanvasProps {
  coords: Coord[];
  demands: number[];
  capacity: number;
  routes: number[][] | null;
  instanceName: string;
}

const COLORS = [
  "#6c8cff", "#4ade80", "#fbbf24", "#f87171", "#a78bfa",
  "#22d3ee", "#fb923c", "#f472b6", "#34d399", "#e879f9",
  "#818cf8", "#2dd4bf", "#facc15", "#fb7185", "#38bdf8",
  "#a3e635", "#c084fc", "#60a5fa", "#f59e0b", "#10b981",
];

function RouteCanvas({ coords, demands, capacity, routes, instanceName }: RouteCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const padding = 60;

    // Clear
    ctx.fillStyle = "#0a0c14";
    ctx.fillRect(0, 0, w, h);

    if (coords.length === 0) {
      ctx.fillStyle = "#8b8fa3";
      ctx.font = "14px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No data", w / 2, h / 2);
      return;
    }

    // Compute bounds
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const c of coords) {
      if (c.x < minX) minX = c.x;
      if (c.x > maxX) maxX = c.x;
      if (c.y < minY) minY = c.y;
      if (c.y > maxY) maxY = c.y;
    }

    const scaleX = (w - 2 * padding) / (maxX - minX || 1);
    const scaleY = (h - 2 * padding) / (maxY - minY || 1);

    function tx(x: number) {
      return padding + (x - minX) * scaleX;
    }
    function ty(y: number) {
      return h - padding - (y - minY) * scaleY; // flip Y
    }

    // Draw grid
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      const gx = padding + (i / 10) * (w - 2 * padding);
      ctx.beginPath();
      ctx.moveTo(gx, padding);
      ctx.lineTo(gx, h - padding);
      ctx.stroke();
      const gy = padding + (i / 10) * (h - 2 * padding);
      ctx.beginPath();
      ctx.moveTo(padding, gy);
      ctx.lineTo(w - padding, gy);
      ctx.stroke();
    }

    // Draw routes
    if (routes && routes.length > 0) {
      for (let ri = 0; ri < routes.length; ri++) {
        const route = routes[ri];
        if (route.length === 0) continue;
        const color = COLORS[ri % COLORS.length];

        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.globalAlpha = 0.85;
        ctx.shadowColor = color;
        ctx.shadowBlur = 6;

        ctx.beginPath();
        // Depot to first
        ctx.moveTo(tx(coords[0].x), ty(coords[0].y));
        ctx.lineTo(tx(coords[route[0]].x), ty(coords[route[0]].y));
        // Route edges
        for (let i = 0; i < route.length - 1; i++) {
          ctx.lineTo(tx(coords[route[i + 1]].x), ty(coords[route[i + 1]].y));
        }
        // Last to depot
        ctx.lineTo(tx(coords[0].x), ty(coords[0].y));
        ctx.stroke();

        ctx.shadowBlur = 0;
        ctx.globalAlpha = 1;

        // Direction arrows
        for (let i = -1; i < route.length; i++) {
          let fromX: number, fromY: number, toX: number, toY: number;
          if (i === -1) {
            fromX = tx(coords[0].x);
            fromY = ty(coords[0].y);
            toX = tx(coords[route[0]].x);
            toY = ty(coords[route[0]].y);
          } else if (i === route.length - 1) {
            fromX = tx(coords[route[i]].x);
            fromY = ty(coords[route[i]].y);
            toX = tx(coords[0].x);
            toY = ty(coords[0].y);
          } else {
            fromX = tx(coords[route[i]].x);
            fromY = ty(coords[route[i]].y);
            toX = tx(coords[route[i + 1]].x);
            toY = ty(coords[route[i + 1]].y);
          }

          const mx = (fromX + toX) / 2;
          const my = (fromY + toY) / 2;
          const dx = toX - fromX;
          const dy = toY - fromY;
          const len = Math.sqrt(dx * dx + dy * dy);
          if (len < 2) continue;
          const ndx = dx / len;
          const ndy = dy / len;

          ctx.fillStyle = color;
          ctx.save();
          ctx.translate(mx, my);
          ctx.rotate(Math.atan2(ndy, ndx));
          ctx.beginPath();
          ctx.moveTo(4, 0);
          ctx.lineTo(-3, -3);
          ctx.lineTo(-3, 3);
          ctx.closePath();
          ctx.fill();
          ctx.restore();
        }
      }
    }

    // Draw depot
    ctx.fillStyle = "#f87171";
    ctx.strokeStyle = "#f87171";
    ctx.lineWidth = 3;
    ctx.shadowColor = "rgba(248,113,113,0.6)";
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(tx(coords[0].x), ty(coords[0].y), 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Label depot
    ctx.fillStyle = "#fff";
    ctx.font = "bold 10px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("D", tx(coords[0].x), ty(coords[0].y));

    // Draw customers
    const maxDemand = Math.max(...demands.slice(1), 1);
    for (let i = 1; i < coords.length; i++) {
      const ratio = demands[i] / maxDemand;
      const radius = 3 + ratio * 5;
      ctx.fillStyle = routes && routes.some(r => r.includes(i))
        ? "rgba(255,255,255,0.9)"
        : "rgba(255,255,255,0.4)";
      ctx.beginPath();
      ctx.arc(tx(coords[i].x), ty(coords[i].y), radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [coords, demands, routes]);

  useEffect(() => {
    draw();
  }, [draw]);

  useEffect(() => {
    const onResize = () => draw();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [draw]);

  return (
    <div ref={containerRef} className="route-canvas-container">
      <canvas ref={canvasRef} />
    </div>
  );
}

// --- Convergence Chart Component ---

function ConvergenceChart({ data }: { data: number[][] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const pad = { top: 30, right: 20, bottom: 40, left: 60 };
    const pw = w - pad.left - pad.right;
    const ph = h - pad.top - pad.bottom;

    ctx.fillStyle = "#0a0c14";
    ctx.fillRect(0, 0, w, h);

    if (!data || data.length === 0 || data[0].length === 0) {
      ctx.fillStyle = "#8b8fa3";
      ctx.font = "13px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Run an experiment to see convergence", w / 2, h / 2);
      return;
    }

    const maxLen = Math.max(...data.map(d => d.length));
    let globalMin = Infinity, globalMax = -Infinity;
    for (const d of data) {
      for (const v of d) {
        if (v < globalMin) globalMin = v;
        if (v > globalMax) globalMax = v;
      }
    }
    if (globalMax - globalMin < 1) {
      globalMin -= 100;
      globalMax += 100;
    }

    function xPos(i: number) {
      return pad.left + (i / (maxLen - 1 || 1)) * pw;
    }
    function yPos(v: number) {
      return pad.top + ph - ((v - globalMin) / (globalMax - globalMin)) * ph;
    }

    // Grid
    ctx.strokeStyle = "rgba(255,255,255,0.04)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = pad.top + (i / 5) * ph;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();

      const val = globalMin + (1 - i / 5) * (globalMax - globalMin);
      ctx.fillStyle = "#8b8fa3";
      ctx.font = "10px Inter, sans-serif";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(Math.round(val).toString(), pad.left - 8, y);
    }

    // X-axis labels
    ctx.fillStyle = "#8b8fa3";
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "center";
    for (let i = 0; i <= 4; i++) {
      const idx = Math.floor((i / 4) * (maxLen - 1));
      const x = xPos(idx);
      ctx.fillText(idx.toString(), x, h - pad.bottom + 20);
    }
    ctx.fillText("Evaluations", w / 2, h - 5);

    // Draw convergence lines for each run
    const runColors = ["#6c8cff", "#4ade80", "#fbbf24", "#f87171", "#a78bfa"];
    for (let r = 0; r < data.length; r++) {
      const run = data[r];
      ctx.strokeStyle = runColors[r % runColors.length];
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.globalAlpha = 0.7;

      ctx.beginPath();
      for (let i = 0; i < run.length; i++) {
        // Scale x to maxLen
        const scaledX = Math.round((i / (run.length - 1)) * (maxLen - 1));
        const x = xPos(scaledX);
        const y = yPos(run[i]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Legend
    const legendY = pad.top;
    for (let r = 0; r < data.length; r++) {
      const x = w - pad.right - 120 + (r % 3) * 45;
      const y = legendY + Math.floor(r / 3) * 16;
      ctx.fillStyle = runColors[r % runColors.length];
      ctx.fillRect(x, y, 10, 10);
      ctx.fillStyle = "#e1e4ed";
      ctx.font = "10px Inter, sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(`Run ${r + 1}`, x + 14, y);
    }
  }, [data]);

  useEffect(() => {
    draw();
  }, [draw]);

  useEffect(() => {
    const onResize = () => draw();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [draw]);

  return (
    <div ref={containerRef} className="convergence-container">
      <canvas ref={canvasRef} />
    </div>
  );
}

// --- Stats Panel Component ---

function StatsPanel({
  results,
  optimal,
}: {
  results: WsExperimentComplete | null;
  optimal: number | null;
}) {
  if (!results) {
    return (
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Best</div>
          <div className="stat-value">-</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Mean</div>
          <div className="stat-value">-</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Std Dev</div>
          <div className="stat-value">-</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Optimal</div>
          <div className="stat-value optimal">-</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Gap %</div>
          <div className="stat-value">-</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Time (s)</div>
          <div className="stat-value">-</div>
        </div>
      </div>
    );
  }

  const gap = optimal ? (((results.best - optimal) / optimal) * 100).toFixed(2) : "-";

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-label">Best</div>
        <div className="stat-value">{Math.round(results.best)}</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Mean</div>
        <div className="stat-value">{Math.round(results.mean)}</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Std Dev</div>
        <div className="stat-value">{Math.round(results.std_dev)}</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Optimal</div>
        <div className="stat-value optimal">{optimal ?? "-"}</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Gap %</div>
        <div className="stat-value">{gap}%</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Time (s)</div>
        <div className="stat-value">{results.execution_time.toFixed(1)}</div>
      </div>
    </div>
  );
}

// --- Main App ---

function App() {
  const [instances, setInstances] = useState<InstanceSet[]>([]);
  const [selectedInstance, setSelectedInstance] = useState("A-n45-k7");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);

  const [coords, setCoords] = useState<Coord[]>([]);
  const [demands, setDemands] = useState<number[]>([]);
  const [capacity, setCapacity] = useState(100);

  const [currentRun, setCurrentRun] = useState(0);
  const [totalRuns, setTotalRuns] = useState(5);
  const [progress, setProgress] = useState(0);
  const [bestCost, setBestCost] = useState<number | null>(null);

  // HGA Configurable Parameters
  const [popSize, setPopSize] = useState(100);
  const [maxEvals, setMaxEvals] = useState(350000);
  const [numRuns, setNumRuns] = useState(5);
  const [crossoverRate, setCrossoverRate] = useState(0.8);
  const [mutationRate, setMutationRate] = useState(0.1);
  const [lsRate, setLsRate] = useState(0.1);
  const [tournamentSize, setTournamentSize] = useState(2);
  const [eliteCount, setEliteCount] = useState(2);
  const [lsMaxIter, setLsMaxIter] = useState(2);
  const [granularSize, setGranularSize] = useState(15);

  const [results, setResults] = useState<WsExperimentComplete | null>(null);
  const [currentRoutes, setCurrentRoutes] = useState<number[][] | null>(null);
  const [optimal, setOptimal] = useState<number | null>(null);

  const [liveConvergence, setLiveConvergence] = useState<number[][]>([]);
  const [completedRuns, setCompletedRuns] = useState<number[]>([]);
  const [elapsedTime, setElapsedTime] = useState(0);
  const startTimeRef = useRef<number>(0);

  const [logs, setLogs] = useState<string[]>([]);

  function addLog(msg: string) {
    setLogs(prev => [...prev.slice(-50), msg]);
  }

  // Load instances on mount
  useEffect(() => {
    fetch("/api/instances")
      .then(r => r.json())
      .then((data: InstanceSet[]) => {
        setInstances(data);
        if (data.length > 0 && data[0].instances.length > 0) {
          setSelectedInstance(data[0].instances[0].name);
        }
      })
      .catch(err => addLog(`Error loading instances: ${err.message}`));

    return () => {
      // cleanup
    };
  }, []);

  // Load selected instance details
  useEffect(() => {
    if (!selectedInstance) return;
    setResults(null);
    setCurrentRoutes(null);
    fetch(`/api/instance/${selectedInstance}`)
      .then(r => r.json())
      .then((data) => {
        const formattedCoords = (data.coords || []).map((c: [number, number]) => ({
          x: c[0],
          y: c[1]
        }));
        setCoords(formattedCoords);
        setDemands(data.demands || []);
        setCapacity(data.capacity || 100);
        setOptimal(data.optimal || null);
      })
      .catch(err => addLog(`Error: ${err.message}`));
  }, [selectedInstance]);

  // Connect WebSocket
  function connectWs() {
    if (ws) {
      ws.close();
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

    socket.onopen = () => {
      setConnected(true);
      addLog("WebSocket connected");
    };

    socket.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data);

      switch (msg.type) {
        case "run_start":
          setCurrentRun(msg.run);
          setTotalRuns(msg.total_runs);
          setCurrentRoutes(null); // Clear routes for the new run
          setLiveConvergence(prev => [...prev, []]);
          addLog(`▶ Run ${msg.run}/${msg.total_runs} - ${msg.instance}`);
          break;
        case "progress":
          setProgress(msg.evaluations / maxEvals);
          setBestCost(msg.best_cost);
          setElapsedTime((Date.now() - startTimeRef.current) / 1000);
          if (msg.routes) {
            setCurrentRoutes(msg.routes);
          }
          setLiveConvergence(prev => {
            const next = prev.map(arr => [...arr]);
            const runIdx = msg.run - 1;
            if (next[runIdx]) {
              next[runIdx].push(msg.best_cost);
            }
            return next;
          });
          break;
        case "run_complete":
          setCurrentRoutes(msg.routes);
          setElapsedTime((Date.now() - startTimeRef.current) / 1000);
          setCompletedRuns(prev => [...prev, msg.cost]);
          addLog(`✓ Run ${msg.run}/${totalRuns} completed: ${Math.round(msg.cost)} (vehicles: ${msg.num_vehicles})`);
          break;
        case "experiment_complete":
          setRunning(false);
          setResults(msg);
          setCurrentRoutes(msg.routes);
          setElapsedTime(msg.execution_time);
          setBestCost(msg.best);
          setProgress(1);
          addLog(`🏆 Experiment complete! Best: ${Math.round(msg.best)}, Mean: ${Math.round(msg.mean)}`);
          break;
        case "error":
          addLog(`⚠ Error: ${msg.message}`);
          setRunning(false);
          break;
      }
    };

    socket.onclose = () => {
      setConnected(false);
      addLog("WebSocket disconnected");
    };

    socket.onerror = () => {
      addLog("WebSocket error");
    };

    setWs(socket);
  }

  // Disconnect on unmount
  useEffect(() => {
    return () => {
      if (ws) ws.close();
    };
  }, [ws]);

  function startExperiment() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      connectWs();
      // Wait for connection then retry
      setTimeout(() => {
        const sock = ws || new WebSocket(`ws://${window.location.host}/ws`);
        sock.onopen = () => {
          sock.send(
            JSON.stringify({
              action: "run",
              instance: selectedInstance,
              max_evals: maxEvals,
              runs: numRuns,
              population_size: popSize,
              crossover_rate: crossoverRate,
              mutation_rate: mutationRate,
              local_search_rate: lsRate,
              tournament_size: tournamentSize,
              elite_count: eliteCount,
              local_search_max_iter: lsMaxIter,
              granular_size: granularSize,
            })
          );
        };
      }, 500);
      return;
    }

    setRunning(true);
    setResults(null);
    setCurrentRoutes(null);
    setLiveConvergence([]);
    setCompletedRuns([]);
    setElapsedTime(0);
    startTimeRef.current = Date.now();
    setProgress(0);
    setLogs([]);
    addLog(`Starting experiment on ${selectedInstance}...`);

    ws.send(
      JSON.stringify({
        action: "run",
        instance: selectedInstance,
        max_evals: maxEvals,
        runs: numRuns,
        population_size: popSize,
        crossover_rate: crossoverRate,
        mutation_rate: mutationRate,
        local_search_rate: lsRate,
        tournament_size: tournamentSize,
        elite_count: eliteCount,
        local_search_max_iter: lsMaxIter,
        granular_size: granularSize,
      })
    );
  }

  // Auto-connect on first render
  useEffect(() => {
    connectWs();
  }, []);

  const selectedOptimal = instances
    .flatMap(s => s.instances)
    .find(i => i.name === selectedInstance)?.optimal ?? optimal;

  const liveResults = results ? results : (running ? (() => {
    const activeCost = bestCost !== null ? [bestCost] : [];
    const allCosts = [...completedRuns, ...activeCost];
    const best = allCosts.length > 0 ? Math.min(...allCosts) : 0;
    const mean = allCosts.length > 0 ? allCosts.reduce((a, b) => a + b, 0) / allCosts.length : 0;
    const std_dev = allCosts.length > 1 ? (() => {
      const m = allCosts.reduce((a, b) => a + b, 0) / allCosts.length;
      const variance = allCosts.reduce((sum, val) => sum + (val - m) ** 2, 0) / allCosts.length;
      return Math.sqrt(variance);
    })() : 0;
    
    return {
      best,
      mean,
      std_dev,
      execution_time: elapsedTime,
      runs: completedRuns,
    } as any;
  })() : null);

  return (
    <>
      <header className="app-header">
        <div>
          <h1>
            CVRP Solver
            <span className="subtitle">Hybrid Genetic Algorithm</span>
          </h1>
        </div>
        <div className="controls">
          <select
            value={selectedInstance}
            onChange={e => setSelectedInstance(e.target.value)}
          >
            {instances.map(set => (
              <optgroup key={set.set} label={`Set ${set.set}`}>
                {set.instances.map(inst => (
                  <option key={inst.name} value={inst.name}>
                    {inst.name} (opt: {inst.optimal}, k={inst.num_vehicles})
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <button
            className="primary"
            onClick={startExperiment}
            disabled={running}
          >
            {running ? "Running..." : "▶ Run Experiment"}
          </button>
          <button
            onClick={connectWs}
            disabled={connected}
          >
            {connected ? "Connected" : "Reconnect"}
          </button>
        </div>
      </header>

      <div className="main-grid">
        {/* Route Visualization */}
        <div className="card" style={{ gridRow: "span 3" }}>
          <h2>Route Visualization</h2>
          <RouteCanvas
            coords={coords}
            demands={demands}
            capacity={capacity}
            routes={currentRoutes ?? results?.routes ?? null}
            instanceName={selectedInstance}
          />
        </div>

        {/* Convergence Chart */}
        <div className="card">
          <h2>Convergence</h2>
          <ConvergenceChart data={liveConvergence.length > 0 ? liveConvergence : (results?.convergence ?? [])} />
        </div>

        {/* Stats */}
        <div className="card">
          <h2>Statistics</h2>
          <StatsPanel results={liveResults} optimal={selectedOptimal} />

          {liveResults && liveResults.runs && liveResults.runs.length > 0 && (
            <div style={{ marginTop: 8, fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Per-run costs: {liveResults.runs.map(c => Math.round(c)).join(", ")}
            </div>
          )}
        </div>

        {/* HGA Parameters */}
        <div className="card">
          <h2>HGA Parameters</h2>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: "12px",
            marginTop: "4px"
          }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Population Size</label>
              <input type="number" value={popSize} onChange={e => setPopSize(Math.max(2, parseInt(e.target.value) || 0))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Max Evaluations</label>
              <input type="number" value={maxEvals} onChange={e => setMaxEvals(Math.max(10, parseInt(e.target.value) || 0))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Runs</label>
              <input type="number" value={numRuns} onChange={e => setNumRuns(Math.max(1, parseInt(e.target.value) || 0))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Crossover Rate</label>
              <input type="number" step="0.05" min="0" max="1" value={crossoverRate} onChange={e => setCrossoverRate(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Mutation Rate</label>
              <input type="number" step="0.05" min="0" max="1" value={mutationRate} onChange={e => setMutationRate(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Local Search Rate</label>
              <input type="number" step="0.05" min="0" max="1" value={lsRate} onChange={e => setLsRate(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Tournament Size</label>
              <input type="number" value={tournamentSize} onChange={e => setTournamentSize(Math.max(1, parseInt(e.target.value) || 0))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Elite Count</label>
              <input type="number" value={eliteCount} onChange={e => setEliteCount(Math.max(0, parseInt(e.target.value) || 0))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>LS Max Iterations</label>
              <input type="number" value={lsMaxIter} onChange={e => setLsMaxIter(Math.max(1, parseInt(e.target.value) || 0))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Granular Size</label>
              <input type="number" value={granularSize} onChange={e => setGranularSize(Math.max(1, parseInt(e.target.value) || 0))} disabled={running} style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem", width: "100%" }} />
            </div>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <span>
          <span className={`status-indicator ${running ? "running" : results ? "complete" : "idle"}`} />
          {running ? `Running run ${currentRun}/${totalRuns}` : results ? "Complete" : "Idle"}
        </span>
        {running && (
          <>
            <span>Best: {bestCost ? Math.round(bestCost) : "-"}</span>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${(progress * 100).toFixed(1)}%` }} />
            </div>
          </>
        )}
        <span style={{ marginLeft: "auto" }}>{connected ? "🟢 WS Connected" : "🔴 WS Disconnected"}</span>
      </div>

      {/* Log */}
      <div className="log-area" style={{ padding: "8px 24px" }}>
        {logs.map((line, i) => (
          <div key={i} className="log-entry">{line}</div>
        ))}
      </div>
    </>
  );
}

export default App;
