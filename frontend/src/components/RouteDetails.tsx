import React from "react";
import { ROUTE_COLORS } from "../config";

export function RouteDetails({
  routes,
  demands,
  capacity,
}: {
  routes: number[][] | null;
  demands: number[];
  capacity: number;
}) {
  if (!routes || routes.length === 0) {
    return (
      <div className="route-detail-list">
        <div
          style={{
            color: "var(--text-muted)",
            fontSize: "0.8rem",
            padding: "20px 8px",
            textAlign: "center",
          }}
        >
          No routes yet
        </div>
      </div>
    );
  }

  return (
    <div className="route-detail-list">
      {routes.map((route, ri) => {
        const load = route.reduce((sum, n) => sum + (demands[n] || 0), 0);
        const pct = Math.min(100, (load / capacity) * 100);
        const barColor =
          pct > 90 ? "#f87171" : pct > 70 ? "#fbbf24" : "#4ade80";
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
                {route.slice(0, 5).join(",")}
                {route.length > 5 ? ` +${route.length - 5}` : ""}
              </span>
              <span className="route-load">{load}/{capacity}</span>
              <span className="route-cost">{cost}</span>
            </div>
            <div className="load-bar-bg">
              <div
                className="load-bar-fill"
                style={{ width: `${pct}%`, background: barColor }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
