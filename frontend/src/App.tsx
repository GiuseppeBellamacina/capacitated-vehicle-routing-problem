import React, { useState, useRef, useCallback, useEffect } from "react";
import { ParamField } from "./components/ParamField";
import { RouteCanvas } from "./components/RouteCanvas";
import { ConvergenceChart } from "./components/ConvergenceChart";
import { RouteDetails } from "./components/RouteDetails";
import { StatsPanel } from "./components/StatsPanel";
import { Collapsible } from "./components/Collapsible";
import { RunBars } from "./components/RunBars";
import { PRESETS, ROUTE_COLORS } from "./config";
import { formatETA } from "./utils";
import {
  InstanceInfo,
  InstanceSet,
  Coord,
  WsExperimentComplete,
  WsMessage,
  Preset,
} from "./types";

// Types and config are imported from shared modules

// --- Main App ---

function useStoredBool(
  key: string,
  fallback: boolean,
): [boolean, (v: boolean) => void] {
  const [value, setValue] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored !== null ? stored === "true" : fallback;
    } catch {
      return fallback;
    }
  });

  const setStored = (v: boolean) => {
    setValue(v);
    try {
      localStorage.setItem(key, String(v));
    } catch {
      /* ignore */
    }
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
  const maxEvalsRef = useRef(maxEvals);
  useEffect(() => {
    maxEvalsRef.current = maxEvals;
  }, [maxEvals]);
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

  const [liveConvergence, setLiveConvergence] = useState<
    { eval: number; cost: number }[][]
  >([]);
  const [completedRuns, setCompletedRuns] = useState<number[]>([]);
  const [elapsedTime, setElapsedTime] = useState(0);
  const startTimeRef = useRef<number>(0);
  const lastUpdateRef = useRef<number>(0);

  const [staleSeconds, setStaleSeconds] = useState(0);
  const [paramsExpanded, setParamsExpanded] = useStoredBool(
    "ui.paramsExpanded",
    false,
  );
  const [advancedExpanded, setAdvancedExpanded] = useStoredBool(
    "ui.advancedExpanded",
    false,
  );

  function addLog(msg: string) {
    console.log(`[Solver Log] ${msg}`);
  }

  const eta =
    running && progress > 0.01 ? (elapsedTime * (1 - progress)) / progress : 0;

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
      .then((r) => r.json())
      .then((data: InstanceSet[]) => {
        setInstances(data);
        if (data.length > 0 && data[0].instances.length > 0) {
          setSelectedInstance(data[0].instances[0].name);
        }
      })
      .catch((err) => addLog(`Error loading instances: ${err.message}`));

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
      .then((r) => r.json())
      .then((data) => {
        const formattedCoords = (data.coords || []).map(
          (c: [number, number]) => ({
            x: c[0],
            y: c[1],
          }),
        );
        setCoords(formattedCoords);
        setDemands(data.demands || []);
        setCapacity(data.capacity || 100);
        setOptimal(data.optimal || null);
      })
      .catch((err) => addLog(`Error: ${err.message}`));
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
          setLiveConvergence((prev) => [...prev, []]);
          addLog(`▶ Run ${msg.run}/${msg.total_runs} - ${msg.instance}`);
          break;
        case "progress":
          lastUpdateRef.current = Date.now();
          setProgress(msg.evaluations / maxEvalsRef.current);
          setBestCost(msg.best_cost);
          setElapsedTime((Date.now() - startTimeRef.current) / 1000);
          if (msg.routes) {
            setCurrentRoutes(msg.routes);
          }
          setLiveConvergence((prev) => {
            const next = prev.map((arr) => [...arr]);
            const runIdx = msg.run - 1;
            if (next[runIdx]) {
              next[runIdx].push({ eval: msg.evaluations, cost: msg.best_cost });
            }
            return next;
          });
          break;
        case "run_complete":
          lastUpdateRef.current = Date.now();
          setCurrentRoutes(msg.routes);
          setElapsedTime((Date.now() - startTimeRef.current) / 1000);
          setCompletedRuns((prev) => [...prev, msg.cost]);
          addLog(
            `✓ Run ${msg.run}/${totalRuns} completed: ${Math.round(msg.cost)} (vehicles: ${msg.num_vehicles})`,
          );
          break;
        case "experiment_complete":
          setRunning(false);
          setResults(msg);
          setCurrentRoutes(msg.routes);
          setElapsedTime(msg.execution_time);
          setBestCost(msg.best);
          setProgress(1);
          addLog(
            `🏆 Experiment complete! Best: ${Math.round(msg.best)}, Mean: ${Math.round(msg.mean)}`,
          );
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
            }),
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
      }),
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

  const selectedOptimal =
    instances
      .flatMap((s) => s.instances)
      .find((i) => i.name === selectedInstance)?.optimal ?? optimal;

  const liveResults = results
    ? results
    : running
      ? (() => {
          const activeCost = bestCost !== null ? [bestCost] : [];
          const allCosts = [...completedRuns, ...activeCost];
          const best = allCosts.length > 0 ? Math.min(...allCosts) : 0;
          const mean =
            allCosts.length > 0
              ? allCosts.reduce((a, b) => a + b, 0) / allCosts.length
              : 0;
          const std_dev =
            allCosts.length > 1
              ? (() => {
                  const m =
                    allCosts.reduce((a, b) => a + b, 0) / allCosts.length;
                  const variance =
                    allCosts.reduce((sum, val) => sum + (val - m) ** 2, 0) /
                    allCosts.length;
                  return Math.sqrt(variance);
                })()
              : 0;

          return {
            best,
            mean,
            std_dev,
            execution_time: elapsedTime,
            runs: completedRuns,
          } as any;
        })()
      : null;

  return (
    <>
      <header className="app-header">
        <div>
          <h1>CVRP Solver</h1>
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
                <span className="preset-label">
                  {activePreset === key ? p.label : p.label.replace("★ ", "")}
                </span>
                <span className="preset-desc">{p.description}</span>
              </button>
            ))}
          </div>
          <select
            value={selectedInstance}
            onChange={(e) => setSelectedInstance(e.target.value)}
          >
            {instances.map((set) => (
              <optgroup key={set.set} label={`Set ${set.set}`}>
                {set.instances.map((inst) => (
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
            <button className="btn btn-danger" onClick={stopExperiment}>
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
        <div className="card">
          <div className="card-header">
            <h2>Route Visualization</h2>
            {currentRoutes && (
              <span className="badge badge-accent">
                {currentRoutes.length} routes
              </span>
            )}
          </div>
          <RouteCanvas
            coords={coords}
            demands={demands}
            routes={currentRoutes ?? results?.routes ?? null}
          />
        </div>

        {/* Right Panel: Accordion Cards */}
        <div className="right-panel">
          {/* Convergence Chart */}
          <div
            className="card card-convergence expanded"
            data-panel="convergence"
          >
            <div className="card-header">
              <h2>Convergence</h2>
            </div>
            <Collapsible expanded={true}>
              <ConvergenceChart
                data={
                  liveConvergence.length > 0
                    ? liveConvergence
                    : (results?.convergence ?? []).map((run) =>
                        run.map((cost, i, arr) => ({
                          eval:
                            arr.length > 1
                              ? Math.round(
                                  (i / (arr.length - 1)) *
                                    (results?.max_evals ?? maxEvals),
                                )
                              : 0,
                          cost,
                        })),
                      )
                }
                maxEvals={results?.max_evals ?? maxEvals}
                optimal={selectedOptimal}
              />
            </Collapsible>
          </div>

          {/* Stats */}
          <div className="card card-stats expanded" data-panel="statistics">
            <div className="card-header">
              <h2>Statistics</h2>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {results && (
                  <span className="badge badge-success">Complete</span>
                )}
                {running && (
                  <span className="badge badge-warning">Running</span>
                )}
              </div>
            </div>
            <Collapsible expanded={true}>
              <StatsPanel results={liveResults} optimal={selectedOptimal} />

              {results?.runs && results.runs.length > 0 && (
                <div
                  style={{
                    marginTop: 4,
                    fontSize: "0.72rem",
                    color: "var(--text-muted)",
                  }}
                >
                  Per-run: {results.runs.map((c) => Math.round(c)).join(", ")}
                </div>
              )}
              {results?.generations_to_best && (
                <div
                  style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}
                >
                  Gens to best:{" "}
                  {results.generations_to_best.map((g) => g).join(", ")}
                </div>
              )}
            </Collapsible>
          </div>

          {/* Route Details */}
          <div className="card card-routes expanded" data-panel="routes">
            <div className="card-header">
              <h2>Route Details</h2>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {currentRoutes && (
                  <span className="badge badge-purple">
                    {currentRoutes.length} vehicles
                  </span>
                )}
              </div>
            </div>
            <Collapsible expanded={true}>
              <RouteDetails
                routes={currentRoutes ?? results?.routes ?? null}
                demands={demands}
                capacity={capacity}
              />
            </Collapsible>
          </div>

          {/* HGA Parameters */}
          <div
            className={`card card-params${paramsExpanded ? " expanded" : ""}`}
            data-panel="params"
          >
            <div
              className="card-header"
              onClick={() => setParamsExpanded(!paramsExpanded)}
            >
              <h2>HGA Parameters</h2>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="badge badge-accent">
                  {activePreset ? activePreset.toUpperCase() : "CUSTOM"}
                </span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  className={`card-toggle-icon${paramsExpanded ? " open" : ""}`}
                >
                  <path
                    d="M4 6L8 10L12 6"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            </div>
            <Collapsible expanded={paramsExpanded}>
              {/* Core parameters — always visible when expanded */}
              <div className="params-grid">
                <ParamField
                  label="Population"
                  value={popSize}
                  onChange={(v) => {
                    setPopSize(v);
                    setActivePreset("");
                  }}
                  disabled={running}
                  min={2}
                  tip="Number of candidate solutions in each generation"
                />
                <ParamField
                  label="Tournament"
                  value={tournamentSize}
                  onChange={(v) => {
                    setTournamentSize(v);
                    setActivePreset("");
                  }}
                  disabled={running}
                  min={1}
                  tip="Individuals competing when selecting parents"
                />
                <ParamField
                  label="Elite"
                  value={eliteCount}
                  onChange={(v) => {
                    setEliteCount(v);
                    setActivePreset("");
                  }}
                  disabled={running}
                  min={0}
                  tip="Top individuals preserved across generations"
                />
                <ParamField
                  label="Granular (GLS)"
                  value={granularSize}
                  onChange={(v) => {
                    setGranularSize(v);
                    setActivePreset("");
                  }}
                  disabled={running}
                  min={1}
                  tip="Penalty granularity for Guided Local Search"
                />
              </div>

              {/* Advanced — collapsible sub-section */}
              <button
                className={`advanced-toggle${advancedExpanded ? " open" : ""}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setAdvancedExpanded(!advancedExpanded);
                }}
                aria-expanded={advancedExpanded}
                aria-label={
                  advancedExpanded
                    ? "Collapse advanced parameters"
                    : "Expand advanced parameters"
                }
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path
                    d="M6 4L10 8L6 12"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Advanced
              </button>

              {advancedExpanded && (
                <div className="params-grid">
                  <ParamField
                    label="Crossover"
                    value={crossoverRate}
                    type="float"
                    step={0.05}
                    min={0}
                    max={1}
                    onChange={(v) => {
                      setCrossoverRate(v);
                      setActivePreset("");
                    }}
                    disabled={running}
                    tip="Probability of recombining two parents"
                  />
                  <ParamField
                    label="Mutation"
                    value={mutationRate}
                    type="float"
                    step={0.05}
                    min={0}
                    max={1}
                    onChange={(v) => {
                      setMutationRate(v);
                      setActivePreset("");
                    }}
                    disabled={running}
                    tip="Probability of randomly altering an offspring"
                  />
                  <ParamField
                    label="LS Rate"
                    value={lsRate}
                    type="float"
                    step={0.05}
                    min={0}
                    max={1}
                    onChange={(v) => {
                      setLsRate(v);
                      setActivePreset("");
                    }}
                    disabled={running}
                    tip="Probability of applying local search to an offspring"
                  />
                  <ParamField
                    label="LS Max Iter"
                    value={lsMaxIter}
                    onChange={(v) => {
                      setLsMaxIter(v);
                      setActivePreset("");
                    }}
                    disabled={running}
                    min={1}
                    tip="Max local-search iterations per application"
                  />
                  <ParamField
                    label="Max Evaluations"
                    value={maxEvals}
                    onChange={(v) => {
                      setMaxEvals(v);
                      setActivePreset("");
                    }}
                    disabled={running}
                    min={10}
                    tip="Total fitness evaluations allowed per run"
                  />
                  <ParamField
                    label="Runs"
                    value={numRuns}
                    onChange={(v) => {
                      setNumRuns(v);
                      setActivePreset("");
                    }}
                    disabled={running}
                    min={1}
                    tip="Independent algorithm repetitions"
                  />
                </div>
              )}
            </Collapsible>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <span>
          <span
            className={`status-dot ${running ? "running" : results ? "complete" : "idle"}`}
          />
          {running
            ? `Run ${currentRun}/${totalRuns}`
            : results
              ? "Experiment Complete"
              : "Ready"}
        </span>
        {running && (
          <>
            <span>
              Best: <strong>{bestCost ? Math.round(bestCost) : "-"}</strong>
            </span>
            <span className="progress-pct">{(progress * 100).toFixed(1)}%</span>
            <div className="progress-bar">
              <div
                className="progress-bar-fill"
                style={{ width: `${(progress * 100).toFixed(1)}%` }}
              />
            </div>
            <RunBars
              totalRuns={totalRuns}
              currentRun={currentRun}
              completedRuns={completedRuns}
              progress={progress}
            />
            <span className={`stale${staleSeconds > 5 ? " blink" : ""}`}>
              {staleSeconds > 0 ? `${staleSeconds}s ago` : "live"}
            </span>
            <span className="eta">
              Elapsed: {formatETA(elapsedTime)} · ~{formatETA(eta)} left
            </span>
          </>
        )}
        <span className={`ws-status ${connected ? "online" : "offline"}`}>
          {connected ? "● WS" : "○ WS"}
        </span>
      </div>
    </>
  );
}

export default App;
