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
  | {  type: "pong" }
  | { type: "experiment_cancelled"; completed_runs: number }
  | { type: "info"; message: string };

// --- Config Presets ---

interface Preset {
  label: string;
  variant: "best" | "accent" | "small-preset" | "warning" | "danger" | "balanced" | "tuned";
  population_size: number;
  tournament_size: number;
  elite_count: number;
  granular_size: number;
  mutation_rate: number;
  crossover_rate: number;
  local_search_rate: number;
  local_search_max_iter: number;
}

const PRESETS: Record<string, Preset> = {
  tuned: {
    label: "★ Tuned", variant: "tuned",
    population_size: 81, tournament_size: 4, elite_count: 4, granular_size: 25,
    mutation_rate: 0.236, crossover_rate: 0.675, local_search_rate: 0.259, local_search_max_iter: 10,
  },
  large: {
    label: "Large", variant: "best",
    population_size: 100, tournament_size: 4, elite_count: 5, granular_size: 15,
    mutation_rate: 0.1, crossover_rate: 0.8, local_search_rate: 0.1, local_search_max_iter: 2,
  },
  balanced: {
    label: "Balanced", variant: "balanced",
    population_size: 60, tournament_size: 3, elite_count: 4, granular_size: 12,
    mutation_rate: 0.1, crossover_rate: 0.85, local_search_rate: 0.1, local_search_max_iter: 2,
  },
  medium: {
    label: "Medium", variant: "accent",
    population_size: 30, tournament_size: 3, elite_count: 3, granular_size: 7,
    mutation_rate: 0.1, crossover_rate: 0.8, local_search_rate: 0.1, local_search_max_iter: 2,
  },
  small: {
    label: "Small", variant: "small-preset",
    population_size: 10, tournament_size: 2, elite_count: 2, granular_size: 3,
    mutation_rate: 0.1, crossover_rate: 0.8, local_search_rate: 0.1, local_search_max_iter: 2,
  },
  fast: {
    label: "Fast", variant: "warning",
    population_size: 5, tournament_size: 2, elite_count: 1, granular_size: 2,
    mutation_rate: 0.1, crossover_rate: 0.8, local_search_rate: 0.1, local_search_max_iter: 2,
  },
  explore: {
    label: "Explore", variant: "danger",
    population_size: 100, tournament_size: 2, elite_count: 1, granular_size: 15,
    mutation_rate: 0.4, crossover_rate: 0.95, local_search_rate: 0.25, local_search_max_iter: 3,
  },
};

const ROUTE_COLORS = [
  "#6c8cff", "#4ade80", "#fbbf24", "#f87171", "#a78bfa",
  "#22d3ee", "#fb923c", "#f472b6", "#34d399", "#e879f9",
  "#818cf8", "#2dd4bf", "#facc15", "#fb7185", "#38bdf8",
  "#a3e635", "#c084fc", "#60a5fa", "#f59e0b", "#10b981",
];

// --- Route Canvas Component ---

interface RouteCanvasProps {
  coords: Coord[];
  demands: number[];
  capacity: number;
  routes: number[][] | null;
  instanceName: string;
}

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

    // ── Square viewport (uniform aspect ratio) ─────────────────────────
    const size = Math.min(w, h);
    const ox = (w - size) / 2;
    const oy = (h - size) / 2;

    // Clear
    ctx.fillStyle = "#0a0c14";
    ctx.fillRect(0, 0, w, h);

    if (coords.length === 0) {
      ctx.fillStyle = "#8b8fa3";
      ctx.font = "14px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No data", ox + size / 2, oy + size / 2);
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

    const dataW = maxX - minX || 1;
    const dataH = maxY - minY || 1;
    const drawSize = size - 2 * padding;
    const scale = Math.min(drawSize / dataW, drawSize / dataH);
    const dataOffX = (drawSize - dataW * scale) / 2;
    const dataOffY = (drawSize - dataH * scale) / 2;

    function tx(x: number) {
      return ox + padding + dataOffX + (x - minX) * scale;
    }
    function ty(y: number) {
      return oy + padding + dataOffY + (maxY - y) * scale;
    }

    // Draw grid (within square)
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    const gx0 = ox + padding; const gy0 = oy + padding;
    const gSize = size - 2 * padding;
    for (let i = 0; i <= 10; i++) {
      const gx = gx0 + (i / 10) * gSize;
      ctx.beginPath();
      ctx.moveTo(gx, gy0);
      ctx.lineTo(gx, gy0 + gSize);
      ctx.stroke();
      const gy = gy0 + (i / 10) * gSize;
      ctx.beginPath();
      ctx.moveTo(gx0, gy);
      ctx.lineTo(gx0 + gSize, gy);
      ctx.stroke();
    }

    // Draw routes
    if (routes && routes.length > 0) {
      for (let ri = 0; ri < routes.length; ri++) {
        const route = routes[ri];
        if (route.length === 0) continue;
        const color = ROUTE_COLORS[ri % ROUTE_COLORS.length];

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
      ctx.fillStyle = routes && routes.some((r: number[]) => r.includes(i))
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

// --- RouteDetails Component ---

function RouteDetails({
  routes,
  demands,
  capacity,
}: {
  routes: number[][] | null;
  demands: number[];
  capacity: number;
}) {
  if (!routes || routes.length === 0) {
    return <div className="route-detail-list"><div style={{color: "var(--text-muted)", fontSize: "0.8rem", padding: "20px 8px", textAlign: "center"}}>No routes yet</div></div>;
  }

  return (
    <div className="route-detail-list">
      {routes.map((route, ri) => {
        const load = route.reduce((sum, n) => sum + (demands[n] || 0), 0);
        const pct = Math.min(100, (load / capacity) * 100);
        const barColor = pct > 90 ? "#f87171" : pct > 70 ? "#fbbf24" : "#4ade80";
        const cost = route.length > 0 ? "-" : "0";

        return (
          <div key={ri}>
            <div className="route-detail-row">
              <span
                className="route-index"
                style={{ background: ROUTE_COLORS[ri % ROUTE_COLORS.length] }}
              >
                {ri + 1}
              </span>
              <span className="route-customers" title={route.join(" → ")}>
                {route.slice(0, 5).join(",")}{route.length > 5 ? ` +${route.length - 5}` : ""}
              </span>
              <span className="route-load">{load}/{capacity}</span>
              <span className="route-cost">{cost}</span>
            </div>
            <div className="load-bar-bg">
              <div className="load-bar-fill" style={{ width: `${pct}%`, background: barColor }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// --- StatsPanel Component ---

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
          <div className="stat-label">Time</div>
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
      <div className="stat-card">        <div className="stat-label">Time</div>
          <div className="stat-value">{formatETA(results.execution_time)}</div>
      </div>
    </div>
  );
}

// --- Collapsible Component ---

function Collapsible({ expanded, children }: { expanded: boolean; children: React.ReactNode }) {
  return (
    <div className={`collapsible${expanded ? " open" : ""}`}>
      <div className="collapsible-inner">{children}</div>
    </div>
  );
}

// --- Toggle Button Component ---

function ToggleButton({ expanded, onToggle, label }: { expanded: boolean; onToggle: () => void; label: string }) {
  return (
    <button
      className={`card-toggle${expanded ? " open" : ""}`}
      onClick={onToggle}
      title={expanded ? "Collapse" : "Expand"}
      aria-label={expanded ? `Collapse ${label}` : `Expand ${label}`}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </button>
  );
}

// --- Run Bars Component ---

function RunBars({ totalRuns, currentRun, completedRuns, progress }: { totalRuns: number; currentRun: number; completedRuns: number[]; progress: number }) {
  return (
    <div className="run-bars">
      {Array.from({ length: totalRuns }, (_, i) => {
        const idx = i + 1;
        const isCompleted = idx < currentRun || completedRuns.length >= idx;
        const isCurrent = idx === currentRun;
        const pct = isCompleted ? 100 : isCurrent ? progress * 100 : 0;
        return (
          <div key={i} className="run-bar">
            <div className={`run-bar-track${isCurrent ? " active" : ""}`}>
              <div
                className={`run-bar-fill${isCompleted ? " done" : ""}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// --- Main App ---

function formatETA(seconds: number): string {
  if (seconds <= 0 || !isFinite(seconds)) return "--";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function useStoredBool(key: string, fallback: boolean): [boolean, (v: boolean) => void] {
  const [value, setValue] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored !== null ? stored === "true" : fallback;
    } catch { return fallback; }
  });

  const setStored = (v: boolean) => {
    setValue(v);
    try { localStorage.setItem(key, String(v)); } catch { /* ignore */ }
  };

  return [value, setStored];
}

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
  const [activePreset, setActivePreset] = useState<string>("large");
  const [maxEvals, setMaxEvals] = useState(350000);
  const [numRuns, setNumRuns] = useState(5);
  const [crossoverRate, setCrossoverRate] = useState(0.8);
  const [mutationRate, setMutationRate] = useState(0.1);
  const [lsRate, setLsRate] = useState(0.1);
  const [tournamentSize, setTournamentSize] = useState(4);
  const [eliteCount, setEliteCount] = useState(5);
  const [lsMaxIter, setLsMaxIter] = useState(2);
  const [granularSize, setGranularSize] = useState(15);

  const [results, setResults] = useState<WsExperimentComplete | null>(null);
  const [currentRoutes, setCurrentRoutes] = useState<number[][] | null>(null);
  const [optimal, setOptimal] = useState<number | null>(null);

  const [liveConvergence, setLiveConvergence] = useState<number[][]>([]);
  const [completedRuns, setCompletedRuns] = useState<number[]>([]);
  const [elapsedTime, setElapsedTime] = useState(0);
  const startTimeRef = useRef<number>(0);
  const lastUpdateRef = useRef<number>(0);

  const [staleSeconds, setStaleSeconds] = useState(0);
  const [paramsExpanded, setParamsExpanded] = useStoredBool("ui.paramsExpanded", false);
  const [advancedExpanded, setAdvancedExpanded] = useStoredBool("ui.advancedExpanded", false);
  const [routesExpanded, setRoutesExpanded] = useStoredBool("ui.routesExpanded", true);
  const [statsExpanded, setStatsExpanded] = useStoredBool("ui.statsExpanded", true);
  const [convExpanded, setConvExpanded] = useStoredBool("ui.convExpanded", true);
  const [logs, setLogs] = useState<string[]>([]);

  function addLog(msg: string) {
    setLogs(prev => [...prev.slice(-50), msg]);
  }

  const eta =
    running && progress > 0.01
      ? (elapsedTime * (1 - progress)) / progress
      : 0;

  function applyPreset(key: string) {
    const p = PRESETS[key];
    if (!p) return;
    setActivePreset(key);
    setPopSize(p.population_size);
    setTournamentSize(p.tournament_size);
    setEliteCount(p.elite_count);
    setGranularSize(p.granular_size);
    setCrossoverRate(p.crossover_rate);
    setMutationRate(p.mutation_rate);
    setLsRate(p.local_search_rate);
    setLsMaxIter(p.local_search_max_iter);
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
          lastUpdateRef.current = Date.now();
          setCurrentRun(msg.run);
          setTotalRuns(msg.total_runs);
          setProgress(0);
          setCurrentRoutes(null);
          setLiveConvergence(prev => [...prev, []]);
          addLog(`▶ Run ${msg.run}/${msg.total_runs} - ${msg.instance}`);
          break;
        case "progress":
          lastUpdateRef.current = Date.now();
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
          lastUpdateRef.current = Date.now();
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
        case "experiment_cancelled":
          setRunning(false);
          setProgress(1);
          addLog(`⏹ Experiment cancelled after ${msg.completed_runs} run(s)`);
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
    lastUpdateRef.current = Date.now();
    setStaleSeconds(0);
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

  function stopExperiment() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ action: "stop" }));
    addLog("⏹ Stop requested — finishing current run...");
  }

  // Auto-connect on first render
  useEffect(() => {
    connectWs();
  }, []);

  // Update stale counter every second during running
  const wasRunningRef = useRef(false);
  useEffect(() => {
    if (!running) {
      if (wasRunningRef.current) setStaleSeconds(0);
      wasRunningRef.current = false;
      return;
    }
    wasRunningRef.current = true;
    const id = setInterval(() => {
      setStaleSeconds(Math.floor((Date.now() - lastUpdateRef.current) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [running]);

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
            <span className="subtitle">HGA · Numba · GLS</span>
          </h1>
        </div>
        <div className="header-right">
          <div className="preset-group">
          {Object.entries(PRESETS).map(([key, p]) => (
            <button
              key={key}
              className={`btn-preset ${p.variant} ${activePreset === key ? "active" : ""}`}
              onClick={() => applyPreset(key)}
              disabled={running}
              title={`μ=${p.population_size}  k=${p.tournament_size}  e=${p.elite_count}  γ=${p.granular_size}  pc=${p.crossover_rate}  pm=${p.mutation_rate}`}
            >
              {activePreset === key ? p.label : p.label.replace("★ ", "")}
            </button>
          ))}
          </div>
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
            className="btn btn-primary"
            onClick={startExperiment}
            disabled={running}
          >
            {running ? "Running..." : "▶ Run"}
          </button>
          {running && (
            <button
              className="btn btn-danger"
              onClick={stopExperiment}
            >
              ■ Stop
            </button>
          )}
          <button
            className="btn"
            onClick={connectWs}
            disabled={connected}
            title="Reconnect WebSocket"
          >
            {connected ? "✓" : "↻"}
          </button>
        </div>
      </header>

      <div className="main-grid">
        {/* Route Visualization */}
        <div className="card" style={{ gridRow: "span 4" }}>
          <div className="card-header">
            <h2>Route Visualization</h2>
            {currentRoutes && (
              <span className="badge badge-accent">{currentRoutes.length} routes</span>
            )}
          </div>
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
          <div className="card-header">
            <h2>Convergence</h2>
            <ToggleButton expanded={convExpanded} onToggle={() => setConvExpanded(!convExpanded)} label="convergence" />
          </div>
          <Collapsible expanded={convExpanded}>
          <ConvergenceChart data={liveConvergence.length > 0 ? liveConvergence : (results?.convergence ?? [])} />
          </Collapsible>
        </div>

        {/* Stats */}
        <div className="card">
          <div className="card-header">
            <h2>Statistics</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {results && <span className="badge badge-success">Complete</span>}
              {running && <span className="badge badge-warning">Running</span>}
              <ToggleButton expanded={statsExpanded} onToggle={() => setStatsExpanded(!statsExpanded)} label="statistics" />
            </div>
          </div>
          <Collapsible expanded={statsExpanded}>
          <StatsPanel results={liveResults} optimal={selectedOptimal} />

          {results?.runs && results.runs.length > 0 && (
            <div style={{ marginTop: 4, fontSize: "0.72rem", color: "var(--text-muted)" }}>
              Per-run: {results.runs.map(c => Math.round(c)).join(", ")}
            </div>
          )}
          {results?.generations_to_best && (
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
              Gens to best: {results.generations_to_best.map(g => g).join(", ")}
            </div>
          )}
          </Collapsible>
        </div>

        {/* Route Details */}
        <div className="card">
          <div className="card-header">
            <h2>Route Details</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {currentRoutes && (
                <span className="badge badge-purple">{currentRoutes.length} vehicles</span>
              )}
              <ToggleButton expanded={routesExpanded} onToggle={() => setRoutesExpanded(!routesExpanded)} label="route details" />
            </div>
          </div>
          <Collapsible expanded={routesExpanded}>
          <RouteDetails routes={currentRoutes ?? results?.routes ?? null} demands={demands} capacity={capacity} />
          </Collapsible>
        </div>

        {/* HGA Parameters */}
        <div className="card">
          <div className="card-header">
            <h2>HGA Parameters</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="badge badge-accent">{activePreset ? activePreset.toUpperCase() : "CUSTOM"}</span>
              <ToggleButton expanded={paramsExpanded} onToggle={() => setParamsExpanded(!paramsExpanded)} label="parameters" />
            </div>
          </div>
          <Collapsible expanded={paramsExpanded}>
          {/* Core parameters — always visible when expanded */}
          <div className="params-grid">
            <div className="param-field">
              <label>Population</label>
              <input type="number" value={popSize} onChange={e => { setPopSize(Math.max(2, parseInt(e.target.value) || 0)); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>Tournament</label>
              <input type="number" value={tournamentSize} onChange={e => { setTournamentSize(Math.max(1, parseInt(e.target.value) || 0)); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>Elite</label>
              <input type="number" value={eliteCount} onChange={e => { setEliteCount(Math.max(0, parseInt(e.target.value) || 0)); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>Granular (GLS)</label>
              <input type="number" value={granularSize} onChange={e => { setGranularSize(Math.max(1, parseInt(e.target.value) || 0)); setActivePreset(""); }} disabled={running} />
            </div>
          </div>

          {/* Advanced — collapsible sub-section */}
          <button
            className={`advanced-toggle${advancedExpanded ? " open" : ""}`}
            onClick={() => setAdvancedExpanded(!advancedExpanded)}
            aria-expanded={advancedExpanded}
            aria-label={advancedExpanded ? "Collapse advanced parameters" : "Expand advanced parameters"}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M6 4L10 8L6 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Advanced
          </button>

          {advancedExpanded && (
          <div className="params-grid">
            <div className="param-field">
              <label>Crossover</label>
              <input type="number" step="0.05" min="0" max="1" value={crossoverRate} onChange={e => { setCrossoverRate(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0))); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>Mutation</label>
              <input type="number" step="0.05" min="0" max="1" value={mutationRate} onChange={e => { setMutationRate(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0))); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>LS Rate</label>
              <input type="number" step="0.05" min="0" max="1" value={lsRate} onChange={e => { setLsRate(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0))); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>LS Max Iter</label>
              <input type="number" value={lsMaxIter} onChange={e => { setLsMaxIter(Math.max(1, parseInt(e.target.value) || 0)); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>Max Evaluations</label>
              <input type="number" value={maxEvals} onChange={e => { setMaxEvals(Math.max(10, parseInt(e.target.value) || 0)); setActivePreset(""); }} disabled={running} />
            </div>
            <div className="param-field">
              <label>Runs</label>
              <input type="number" value={numRuns} onChange={e => { setNumRuns(Math.max(1, parseInt(e.target.value) || 0)); setActivePreset(""); }} disabled={running} />
            </div>
          </div>
          )}
          </Collapsible>
        </div>
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <span>
          <span className={`status-dot ${running ? "running" : results ? "complete" : "idle"}`} />
          {running ? `Run ${currentRun}/${totalRuns}` : results ? "Experiment Complete" : "Ready"}
        </span>
        {running && (
          <>
            <span>Best: <strong>{bestCost ? Math.round(bestCost) : "-"}</strong></span>
            <span className="progress-pct">{(progress * 100).toFixed(1)}%</span>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${(progress * 100).toFixed(1)}%` }} />
            </div>
            <RunBars totalRuns={totalRuns} currentRun={currentRun} completedRuns={completedRuns} progress={progress} />
            <span className={`stale${staleSeconds > 5 ? " blink" : ""}`}>
              {staleSeconds > 0 ? `${staleSeconds}s ago` : "live"}
            </span>
            <span className="eta">Elapsed: {formatETA(elapsedTime)} · ~{formatETA(eta)} left</span>
          </>
        )}
        <span className={`ws-status ${connected ? "online" : "offline"}`}>
          {connected ? "● WS" : "○ WS"}
        </span>
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
