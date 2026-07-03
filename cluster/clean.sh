#!/bin/bash
# ============================================================================
# Pulizia workspace sul cluster DMI — CVRP Solver (HGA)
#
# Uso:
#   bash cluster/clean.sh          # dry-run (mostra cosa cancellerebbe)
#   bash cluster/clean.sh --force  # cancella davvero
# ============================================================================

set -e

PROJ_DIR="$HOME/capacitated-vehicle-routing-problem"
cd "$PROJ_DIR"

FORCE=0
if [ "$1" = "--force" ]; then
    FORCE=1
fi

if [ "$FORCE" = "0" ]; then
    echo "=== DRY RUN — aggiungi --force per cancellare davvero ==="
    echo ""
    CMD="echo [DRY] rm -rf"
else
    CMD="rm -rf"
fi

echo "Pulizia workspace: $PWD"
echo ""

# ── [1/7] Risultati esperimenti ──────────────────────────────────────────
echo "[1/7] results/ (risultati esperimenti)"
if [ -d "results" ]; then
    $CMD results/*
fi

# ── [2/7] Grafici generati ───────────────────────────────────────────────
echo "[2/7] docs/report/imgs/ (grafici)"
if [ -d "docs/report/imgs" ]; then
    $CMD docs/report/imgs/convergence/*
    $CMD docs/report/imgs/routes/*
    $CMD docs/report/imgs/summary/*
fi

# ── [3/7] Log SLURM ──────────────────────────────────────────────────────
echo "[3/7] logs/ (SLURM output)"
if [ -d "logs" ]; then
    $CMD logs/*
fi

# ── [4/7] Cache Python ───────────────────────────────────────────────────
echo "[4/7] __pycache__/"
find . -type d -name "__pycache__" -print -exec $CMD {} + 2>/dev/null || true

# ── [5/7] File temporanei ────────────────────────────────────────────────
echo "[5/7] File .tmp/"
find . -name "*.tmp" -type f -print -exec $CMD {} + 2>/dev/null || true

# ── [6/7] Directory .ruff_cache ──────────────────────────────────────────
echo "[6/7] .ruff_cache/"
if [ -d "backend/.ruff_cache" ]; then
    $CMD backend/.ruff_cache
fi

# ── [7/7] Checkpoint Numba (cache JIT) ───────────────────────────────────
echo "[7/7] __pycache__/numba/"
find . -path "*/numba*" -type d -print -exec $CMD {} + 2>/dev/null || true

echo ""
if [ "$FORCE" = "0" ]; then
    echo "=== Nessun file cancellato (dry-run). Usa: bash cluster/clean.sh --force ==="
else
    echo "✅ Pulizia completata."
fi
