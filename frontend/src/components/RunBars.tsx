import React from "react";

export function RunBars({
  totalRuns,
  currentRun,
  completedRuns,
  progress,
}: {
  totalRuns: number;
  currentRun: number;
  completedRuns: number[];
  progress: number;
}) {
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
