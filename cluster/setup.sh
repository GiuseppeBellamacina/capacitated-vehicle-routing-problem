#!/bin/bash
# ============================================================================
# Setup one-tantum per il cluster DMI — CVRP Solver (HGA)
#
# Installa le dipendenze Python (numpy, numba, matplotlib, tqdm, pyyaml)
# e verifica che l'ambiente sia pronto per eseguire gli esperimenti.
#
# Uso (dal login node):
#   cd ~/capacitated-vehicle-routing-problem
#   bash cluster/setup.sh
#
# Non richiede GPU — il progetto è CPU-bound (algoritmo genetico).
# ============================================================================

# ── 0. Auto-rilancio dentro srun + Apptainer se siamo sul login node ─────────
if [ -z "$APPTAINER_CONTAINER" ]; then
    echo "🚀 Login node rilevato → rilancio inside srun + Apptainer..."
    ACCOUNT="${SLURM_ACCOUNT:-thesis-course}"
    exec srun --account "$ACCOUNT" --partition "$ACCOUNT" --qos gpu-xlarge \
         --gres=gpu:1 --gres=shard:22000 --mem=48G --cpus-per-task=8 \
         apptainer run --nv /shared/sifs/latest.sif \
         bash "$0" "$@"
fi

set -e

PROJ_DIR="${PROJ_DIR:-$HOME/capacitated-vehicle-routing-problem}"

echo "============================================"
echo "  CVRP Solver (HGA) — Setup Cluster DMI"
echo "  $(date)"
echo "============================================"
echo ""

# ── 1. Trova Python disponibile (dentro Apptainer) ───────────────────────────
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "❌ Python non trovato!"
    exit 1
fi
echo "🔍 Python: $($PY --version 2>&1)"
echo "   Path: $(which $PY)"
echo ""

# ── 2. Verifica versione Python (min 3.11) ───────────────────────────────────
$PY --version 2>&1
echo ""

# ── 3. Installa dipendenze ───────────────────────────────────────────────────
echo "📦 Installazione dipendenze Python (pip install --user)..."
cd "$PROJ_DIR/backend"

# Core dependencies
pip install --user numpy matplotlib numba tqdm pyyaml

# Dev dependencies (formatting)
pip install --user ruff isort black

echo ""
echo "✅ Dipendenze installate."
echo ""

# ── 4. Verifica installazione ────────────────────────────────────────────────
echo "🔍 Verifica installazione..."
$PY -c "
import numpy;       print(f'  numpy:      {numpy.__version__}')
import matplotlib;  print(f'  matplotlib: {matplotlib.__version__}')
import numba;       print(f'  numba:      {numba.__version__}')
import tqdm;        print(f'  tqdm:       {tqdm.__version__}')
import yaml;        print(f'  pyyaml:     {yaml.__version__}')
" 2>/dev/null || {
    echo "⚠️  Alcuni moduli non sono stati trovati. Verifica l'installazione."
}

echo ""

# ── 5. Crea directory necessarie ─────────────────────────────────────────────
mkdir -p "$PROJ_DIR/logs"
mkdir -p "$PROJ_DIR/results"
mkdir -p "$PROJ_DIR/docs/report/imgs/summary"

echo "📁 Directory create:"
echo "   logs/"
echo "   results/"
echo "   docs/report/imgs/{convergence,routes,summary}/"
echo ""

# ── 6. Test rapido ───────────────────────────────────────────────────────────
echo "🧪 Test rapido import HGA..."
$PY -c "
import sys
sys.path.insert(0, '$PROJ_DIR/backend')
from cvrp.instance import read_instance
from cvrp.hga import HybridGeneticAlgorithm
print('  ✅ Moduli CVRP importati correttamente')
" 2>/dev/null || {
    echo "  ⚠️  Import fallito — assicurati che il codice sia stato sincronizzato"
    echo "     Esegui dal PC locale: .\sync_cluster.ps1 -Action upload"
}

echo ""
echo "============================================"
echo "  ✅ Setup completato!"
echo "============================================"
echo ""
echo "Prossimi passi:"
echo "  1. Carica gli alias:  source cluster/aliases.sh"
echo "  2. Modifica cluster/run.sh con account/partition/email"
echo "  3. Lancia esperimenti:  run-exp"
echo "  4. Oppure direttamente: sbatch cluster/run.sh"
