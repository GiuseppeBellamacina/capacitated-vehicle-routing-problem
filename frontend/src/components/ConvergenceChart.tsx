import React, { useRef, useCallback, useEffect } from "react";

function formatEval(n: number): string {
  if (n >= 1000) {
    const k = n / 1000;
    if (k === Math.floor(k)) return `${k}k`;
    return `${k.toFixed(1)}k`;
  }
  return n.toString();
}

function drawStar(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  spikes: number,
  outerR: number,
  innerR: number
) {
  let rot = (Math.PI / 2) * 3;
  const step = Math.PI / spikes;
  ctx.beginPath();
  ctx.moveTo(cx, cy - outerR);
  for (let i = 0; i < spikes; i++) {
    ctx.lineTo(
      cx + Math.cos(rot) * outerR,
      cy + Math.sin(rot) * outerR
    );
    rot += step;
    ctx.lineTo(
      cx + Math.cos(rot) * innerR,
      cy + Math.sin(rot) * innerR
    );
    rot += step;
  }
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}

export function ConvergenceChart({
  data,
  maxEvals,
  optimal,
}: {
  data: { eval: number; cost: number }[][];
  maxEvals: number;
  optimal: number | null;
}) {
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

    let globalMin = Infinity,
      globalMax = -Infinity;
    for (const d of data) {
      for (const point of d) {
        if (point.cost < globalMin) globalMin = point.cost;
        if (point.cost > globalMax) globalMax = point.cost;
      }
    }
    if (optimal !== null) {
      if (optimal < globalMin) globalMin = optimal;
      if (optimal > globalMax) globalMax = optimal;
    }
    if (globalMax - globalMin < 1) {
      globalMin -= 100;
      globalMax += 100;
    }

    function xPos(evalVal: number) {
      return pad.left + (evalVal / maxEvals) * pw;
    }
    function yPos(v: number) {
      return pad.top + ph - ((v - globalMin) / (globalMax - globalMin)) * ph;
    }

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

    ctx.fillStyle = "#8b8fa3";
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "center";
    for (let i = 0; i <= 4; i++) {
      const evalVal = (i / 4) * maxEvals;
      const x = xPos(evalVal);
      ctx.fillText(formatEval(evalVal), x, h - pad.bottom + 20);
    }
    ctx.fillText("Evaluations", w / 2, h - 5);

    if (optimal !== null) {
      const oy = yPos(optimal);
      ctx.strokeStyle = "#34d399";
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.55;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(pad.left, oy);
      ctx.lineTo(w - pad.right, oy);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;

      ctx.fillStyle = "#34d399";
      ctx.font = "bold 9px Inter, sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      ctx.fillText(`Optimal: ${Math.round(optimal)}`, pad.left + 6, oy - 3);
    }

    const runColors = [
      "#6c8cff",
      "#4ade80",
      "#fbbf24",
      "#f87171",
      "#a78bfa",
    ];
    for (let r = 0; r < data.length; r++) {
      const run = data[r];
      ctx.strokeStyle = runColors[r % runColors.length];
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.globalAlpha = 0.7;

      ctx.beginPath();
      for (let i = 0; i < run.length; i++) {
        const x = xPos(run[i].eval);
        const y = yPos(run[i].cost);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    for (let r = 0; r < data.length; r++) {
      const run = data[r];
      if (run.length === 0) continue;

      let minCost = run[0].cost;
      let bestIdx = 0;
      for (let i = 1; i < run.length; i++) {
        if (run[i].cost < minCost) {
          minCost = run[i].cost;
          bestIdx = i;
        }
      }

      const bestPoint = run[bestIdx];
      const mx = xPos(bestPoint.eval);
      const my = yPos(bestPoint.cost);
      const color = runColors[r % runColors.length];

      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.35;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(mx, my);
      ctx.lineTo(mx, pad.top + ph);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;

      ctx.fillStyle = color;
      ctx.strokeStyle = "#0a0c14";
      ctx.lineWidth = 2;
      ctx.shadowColor = color;
      ctx.shadowBlur = 8;
      drawStar(ctx, mx, my, 5, 7, 3);
      ctx.shadowBlur = 0;

      if (my > pad.top + 14) {
        ctx.fillStyle = color;
        ctx.font = "bold 9px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(`★ ${formatEval(bestPoint.eval)}`, mx, my - 10);
      }
    }

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
  }, [data, maxEvals, optimal]);

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
