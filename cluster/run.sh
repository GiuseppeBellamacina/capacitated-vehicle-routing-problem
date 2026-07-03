#!/bin/bash
# ============================================================================
# SLURM batch script — CVRP Solver (HGA)
#
# Esegue in sequenza:
#   1. Esperimenti (run_experiments.py) su tutte le 10 istanze
#   2. Grafici (plot_convergence.py) — 9 tipi di grafico
#   3. Tabella LaTeX (format_latex_table.py) — output salvato in results/table.txt
#
# Uso:
#   sbatch cluster/run.sh
#
# Oppure con config personalizzato:
#   CONFIG=../config/config.yaml sbatch cluster/run.sh
# ============================================================================

# ┌────────────────────────────────────────────────────────┐
# │  CONFIGURA QUI — modifica account/partition/qos/email  │
# └────────────────────────────────────────────────────────┘
#SBATCH --job-name=train
#SBATCH --account=thesis-course
#SBATCH --partition=thesis-course
#SBATCH --mem=8G
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=bellamacina50@gmail.com
#SBATCH --output=logs/slurm-train-%j.log

# ── Variabili ─────────────────────────────────────────────────────────────────
# CONFIG: path relativo al progetto per un file di configurazione alternativo.
# Se impostato, sovrascrive temporaneamente config/config.yaml prima degli esperimenti.
CONFIG="${CONFIG:-}"
PROJ_DIR="$HOME/capacitated-vehicle-routing-problem"

set -e

echo "============================================"
echo "  CVRP Solver (HGA) — Cluster DMI"
echo "  Job ID:    ${SLURM_JOB_ID}"
echo "  Node:      $(hostname)"
echo "  Date:      $(date)"
echo "============================================"
echo ""

cd "$PROJ_DIR/backend"

# Trova Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "❌ Python non trovato!"
    exit 1
fi

echo "Python: $($PY --version 2>&1)"

# ── 0. Configurazione ────────────────────────────────────────────────────────
# Se CONFIG è stato passato (es. CONFIG=../config/custom.yaml sbatch ...),
# sovrascrivi config/config.yaml per questa esecuzione.
# La trap EXIT ripristina automaticamente il config originale in ogni caso.
CONFIG_ORIG_BACKUP=""
trap 'if [ -n "$CONFIG_ORIG_BACKUP" ] && [ -f "$CONFIG_ORIG_BACKUP" ]; then mv "$CONFIG_ORIG_BACKUP" "$PROJ_DIR/config/config.yaml"; fi' EXIT

if [ -n "$CONFIG" ] && [ -f "$PROJ_DIR/$CONFIG" ]; then
    DEFAULT_CONFIG="$PROJ_DIR/config/config.yaml"
    if [ -f "$DEFAULT_CONFIG" ]; then
        cp "$DEFAULT_CONFIG" "${DEFAULT_CONFIG}.bak"
        CONFIG_ORIG_BACKUP="${DEFAULT_CONFIG}.bak"
    fi
    cp "$PROJ_DIR/$CONFIG" "$DEFAULT_CONFIG"
    echo "📋 Configurazione: $CONFIG → config/config.yaml"
elif [ -n "$CONFIG" ]; then
    echo "⚠️  Config '$CONFIG' non trovato — uso config/config.yaml di default"
else
    echo "📋 Configurazione: config/config.yaml (default)"
fi

# ── 1. Esperimenti ───────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  [1/3] ESPERIMENTI — run_experiments.py"
echo "════════════════════════════════════════════"
echo ""

START_EXP=$(date +%s)

$PY run_experiments.py
EXP_EXIT=$?

END_EXP=$(date +%s)
EXP_ELAPSED=$((END_EXP - START_EXP))
echo ""
echo "✅ Esperimenti completati in ${EXP_ELAPSED}s (exit code: $EXP_EXIT)"

if [ $EXP_EXIT -ne 0 ]; then
    echo "❌ Esperimenti falliti (exit code: $EXP_EXIT) — interrompo."
    exit $EXP_EXIT
fi

# ── 2. Grafici ───────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  [2/3] GRAFICI — plot_convergence.py"
echo "════════════════════════════════════════════"
echo ""

$PY plot_convergence.py
PLOT_EXIT=$?

if [ $PLOT_EXIT -ne 0 ]; then
    echo "⚠️  Generazione grafici fallita (exit code: $PLOT_EXIT) — continuo con la tabella."
else
    echo ""
    echo "✅ Grafici generati in docs/report/imgs/{convergence,routes,summary}/"
fi

# ── 3. Tabella LaTeX ─────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  [3/3] TABELLA — format_latex_table.py"
echo "════════════════════════════════════════════"
echo ""

TABLE_OUT="$PROJ_DIR/results/table.txt"
$PY format_latex_table.py | tee "$TABLE_OUT"
TABLE_EXIT=${PIPESTATUS[0]}

echo ""
echo "📄 Tabella LaTeX salvata in: results/table.txt"

# ── Riepilogo ─────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ PIPELINE COMPLETATA"
echo "  $(date)"
echo "============================================"
echo ""
echo "Output generati:"
echo "  results/results.json              — risultati esperimenti"
echo "  results/table.txt                 — tabella LaTeX"
echo "  docs/report/imgs/convergence/     — grafici convergenza"
echo "  docs/report/imgs/routes/          — grafici rotte"
echo "  docs/report/imgs/summary/         — grafici riepilogativi"
echo ""

if [ $PLOT_EXIT -ne 0 ] || [ $TABLE_EXIT -ne 0 ]; then
    echo "⚠️  Completato con warnings: plot=$PLOT_EXIT table=$TABLE_EXIT"
    exit 1
fi

exit 0
