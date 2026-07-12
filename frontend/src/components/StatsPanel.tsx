import React from "react";
import { WsExperimentComplete } from "../types";
import { formatETA } from "../utils";

export function StatsPanel({
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

  const gap = optimal
    ? (((results.best - optimal) / optimal) * 100).toFixed(2)
    : "-";

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
        <div className="stat-label">Time</div>
        <div className="stat-value">{formatETA(results.execution_time)}</div>
      </div>
    </div>
  );
}
