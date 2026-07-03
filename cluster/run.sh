#!/bin/bash
# ============================================================================
# SLURM batch script — CVRP Solver (HGA)
#
# Esegue in sequenza per OGNI variante di configurazione:
#   1. Esperimenti (run_experiments.py) su tutte le 10 istanze
#   2. Grafici (plot_convergence.py) — 10 tipi di grafico
#   3. Tabella LaTeX (format_latex_table.py)
#
# Ogni config YAML contiene già i path di output (output_dir, imgs_dir).
# Nessun env var, nessun backup/restore — pulito e semplice.
#
# Uso:
#   sbatch cluster/run.sh
# ============================================================================

# ┌────────────────────────────────────────────────────────┐
# │  CONFIGURA QUI — modifica account/partition/qos/email  │
# └────────────────────────────────────────────────────────┘
#SBATCH --job-name=train
#SBATCH --account=thesis-course
#SBATCH --partition=thesis-course
#SBATCH --qos=gpu-xlarge
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1 --gres=shard:22528
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=bellamacina50@gmail.com
#SBATCH --output=logs/slurm-train-%j.log

set -e -o pipefail

PROJ_DIR="$HOME/capacitated-vehicle-routing-problem"

echo "============================================"
echo "  CVRP Solver (HGA) — Multi-Config Pipeline"
echo "  Job ID:    ${SLURM_JOB_ID}"
echo "  Node:      $(hostname)"
echo "  Date:      $(date)"
echo "============================================"
echo ""

cd "$PROJ_DIR/backend"

# ── Configs da eseguire in sequenza (auto-discovery) ──────────────────────────
# Scansiona config/config_*.yaml in ordine alfabetico — nuove config
# vengono automaticamente incluse senza modificare questo script.
readarray -t CONFIGS < <(ls -1 "$PROJ_DIR"/config/config_*.yaml 2>/dev/null | sort)

if [ ${#CONFIGS[@]} -eq 0 ]; then
    echo "Errore: nessun file config/config_*.yaml trovato."
    exit 1
fi

TOTAL=${#CONFIGS[@]}
NUM=0

for CFG_FILE in "${CONFIGS[@]}"; do
    NUM=$((NUM + 1))
    CFG_PATH="${CFG_FILE#$PROJ_DIR/}"
    CFG=$(basename "$CFG_FILE" .yaml)

    # Legge output_dir e imgs_dir direttamente dal file YAML (senza Python)
    OUTPUT_DIR=$(grep '^output_dir:' "$CFG_FILE" | awk '{print $2}')
    IMGS_DIR=$(grep '^imgs_dir:' "$CFG_FILE" | awk '{print $2}')

    RESULTS_FILE="$PROJ_DIR/${OUTPUT_DIR}/results.json"
    TABLE_FILE="$PROJ_DIR/${OUTPUT_DIR}/table.txt"
    IMGS_BASE="$PROJ_DIR/${IMGS_DIR}"

    echo "╔═════════════════════════════════════╗"
    echo "║  [${NUM}/${TOTAL}] Config: ${CFG}"  ║
    echo "╚═════════════════════════════════════╝"
    echo "  Config:   ${CFG_PATH}"
    echo "  Results:  ${OUTPUT_DIR}/"
    echo "  Images:   ${IMGS_DIR}/"
    echo ""

    # Crea directory di output
    mkdir -p "$PROJ_DIR/${OUTPUT_DIR}"
    mkdir -p "${IMGS_BASE}/convergence"
    mkdir -p "${IMGS_BASE}/routes"
    mkdir -p "${IMGS_BASE}/summary"

    APPT="apptainer run /shared/sifs/latest.sif python3"

    # ── 1. Esperimenti ───────────────────────────────────────────────────
    echo "  ════════════════════════════════════════"
    echo "  [${NUM}a] ESPERIMENTI — run_experiments.py"
    echo "  ════════════════════════════════════════"
    echo ""

    START_EXP=$(date +%s)

    $APPT run_experiments.py --config "../$CFG_PATH"
    EXP_EXIT=$?

    END_EXP=$(date +%s)
    echo ""
    echo "  ✅ Esperimenti ${CFG} completati in $((END_EXP - START_EXP))s"

    if [ $EXP_EXIT -ne 0 ]; then
        echo "  ❌ Esperimenti ${CFG} falliti — interrompo."
        exit $EXP_EXIT
    fi

    # ── 2. Grafici ───────────────────────────────────────────────────────
    echo ""
    echo "  ════════════════════════════════════════"
    echo "  [${NUM}b] GRAFICI — plot_convergence.py"
    echo "  ════════════════════════════════════════"
    echo ""

    $APPT plot_convergence.py --results "../${OUTPUT_DIR}/results.json" --imgs "../${IMGS_DIR}"
    PLOT_EXIT=$?

    if [ $PLOT_EXIT -ne 0 ]; then
        echo "  ⚠️  Grafici ${CFG} falliti — continuo."
    else
        echo "  ✅ Grafici ${CFG} → ${IMGS_DIR}/"
    fi

    # ── 3. Tabella LaTeX ─────────────────────────────────────────────────
    echo ""
    echo "  ════════════════════════════════════════"
    echo "  [${NUM}c] TABELLA — format_latex_table.py"
    echo "  ════════════════════════════════════════"
    echo ""

    $APPT format_latex_table.py --results "../${OUTPUT_DIR}/results.json" | tee "$TABLE_FILE"
    TABLE_EXIT=${PIPESTATUS[0]}

    echo ""
    echo "  📄 Tabella ${CFG}: ${OUTPUT_DIR}/table.txt"
    echo ""
done

# ── Config comparison chart (generato una sola volta con tutti i dati) ────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  CONFIG COMPARISON — summary_config_comparison.png"  ║
echo "╚══════════════════════════════════════════════════════╝"
echo ""

$APPT plot_convergence.py --comparison-only
CMP_EXIT=$?

if [ $CMP_EXIT -ne 0 ]; then
    echo "  ⚠️  Config comparison fallito (potrebbero servire più config completate)."
else
    echo "  ✅ Config comparison → docs/report/imgs/summary/summary_config_comparison.png"
fi

# ── Tabella LaTeX comparativa (una sola con tutte le config affiancate) ────────
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  TABLE COMPARISON — table_comparison.txt"  ║
echo "╚════════════════════════════════════════════╝"
echo ""

TABLE_COMP="$PROJ_DIR/results/table_comparison.txt"
$APPT format_latex_comparison.py --output ../results/table_comparison.txt 2>&1
echo ""
if [ -f "$TABLE_COMP" ]; then
    echo "  ✅ Tabella comparativa → results/table_comparison.txt"
else
    echo "  ⚠️  Tabella comparativa fallita."
fi

# ── Riepilogo ─────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ PIPELINE COMPLETATA — ${TOTAL} config"
echo "  $(date)"
echo "============================================"
echo ""
echo "Output generati:"
echo "  docs/report/imgs/summary/summary_config_comparison.png"
echo "  results/table_comparison.txt"
for CFG_FILE in "${CONFIGS[@]}"; do
    CFG=$(basename "$CFG_FILE" .yaml)
    OUTPUT_DIR=$(grep '^output_dir:' "$CFG_FILE" | awk '{print $2}')
    IMGS_DIR=$(grep '^imgs_dir:' "$CFG_FILE" | awk '{print $2}')
    echo "  ${OUTPUT_DIR}/results.json"
    echo "  ${OUTPUT_DIR}/table.txt"
    echo "  ${IMGS_DIR}/{convergence,routes,summary}/"
done
echo ""

exit 0
