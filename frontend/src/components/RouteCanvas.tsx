import React, { useRef, useCallback, useEffect } from "react";
import { ROUTE_COLORS } from "../config";
import { Coord } from "../types";

interface RouteCanvasProps {
  coords: Coord[];
  demands: number[];
  routes: number[][] | null;
}

export function RouteCanvas({
  coords,
  demands,
  routes,
}: RouteCanvasProps) {
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
    const padding = 20;

    const size = Math.min(w, h);
    const ox = (w - size) / 2;
    const oy = (h - size) / 2;

    ctx.fillStyle = "#0a0c14";
    ctx.fillRect(0, 0, w, h);

    if (coords.length === 0) {
      ctx.fillStyle = "#8b8fa3";
      ctx.font = "14px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No data", ox + size / 2, oy + size / 2);
      return;
    }

    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;
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

    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    const gx0 = ox + padding;
    const gy0 = oy + padding;
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
        ctx.moveTo(tx(coords[0].x), ty(coords[0].y));
        ctx.lineTo(tx(coords[route[0]].x), ty(coords[route[0]].y));
        for (let i = 0; i < route.length - 1; i++) {
          ctx.lineTo(tx(coords[route[i + 1]].x), ty(coords[route[i + 1]].y));
        }
        ctx.lineTo(tx(coords[0].x), ty(coords[0].y));
        ctx.stroke();

        ctx.shadowBlur = 0;
        ctx.globalAlpha = 1;

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

    ctx.fillStyle = "#fff";
    ctx.font = "bold 10px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("D", tx(coords[0].x), ty(coords[0].y));

    const maxDemand = Math.max(...demands.slice(1), 1);
    for (let i = 1; i < coords.length; i++) {
      const ratio = demands[i] / maxDemand;
      const radius = 3 + ratio * 5;
      ctx.fillStyle =
        routes && routes.some((r: number[]) => r.includes(i))
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
