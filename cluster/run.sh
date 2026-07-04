#!/bin/bash
# ============================================================================
# SLURM batch script — CVRP Solver (HGA)
#
# Esegue in sequenza per ogni variante di configurazione:
#   1. Esperimenti (run_experiments.py) su tutte le 10 istanze
#   2. Grafici (plot_convergence.py)
#   3. Tabella LaTeX (format_latex.py)
#
# Uso:
#   sbatch cluster/run.sh                   # tutti i config
#   sbatch cluster/run.sh config_explore    # solo config_explore
#   sbatch cluster/run.sh config_large      # solo config_large
#
#   Con sbatch, l'argomento va DOPO lo script:
#     sbatch cluster/run.sh config_explore
#   In locale (test):
#     bash cluster/run.sh config_explore
# ============================================================================

#Job name: il nome del config se passato, altrimenti "cvrp-all"
#SBATCH --job-name=cvrp
#SBATCH --account=thesis-course
#SBATCH --partition=thesis-course
#SBATCH --qos=gpu-xlarge
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1 --gres=shard:22528
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=bellamacina50@gmail.com
#SBATCH --output=logs/slurm-cvrp-%j.log

set -e -o pipefail

PROJ_DIR="$HOME/capacitated-vehicle-routing-problem"
CONFIG_ARG="${1:-}"   # nome config passato come argomento (opzionale)

echo "============================================"
echo "  CVRP Solver (HGA) — Pipeline"
if [ -n "$CONFIG_ARG" ]; then
    echo "  Config:    ${CONFIG_ARG} (single)"
else
    echo "  Config:    ALL (auto-discovery)"
fi
echo "  Job ID:    ${SLURM_JOB_ID}"
echo "  Node:      $(hostname)"
echo "  Date:      $(date)"
echo "============================================"
echo ""

cd "$PROJ_DIR/backend"

# ── Configs da eseguire ──────────────────────────────────────────────────────
if [ -n "$CONFIG_ARG" ]; then
    # Modalità single-config: passa il nome (es. config_explore)
    CFG_FILE="$PROJ_DIR/config/${CONFIG_ARG}.yaml"
    if [ ! -f "$CFG_FILE" ]; then
        echo "Errore: file '$CFG_FILE' non trovato."
        echo "Config disponibili:"
        ls -1 "$PROJ_DIR"/config/config_*.yaml 2>/dev/null | sed 's/.*\///; s/\.yaml//' || true
        exit 1
    fi
    CONFIGS=("$CFG_FILE")
else
    # Modalità auto-discovery: tutti i config/config_*.yaml
    readarray -t CONFIGS < <(ls -1 "$PROJ_DIR"/config/config_*.yaml 2>/dev/null | sort)
    if [ ${#CONFIGS[@]} -eq 0 ]; then
        echo "Errore: nessun file config/config_*.yaml trovato."
        exit 1
    fi
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

    EXP_EXIT=0
    $APPT run_experiments.py --config "../$CFG_PATH" || EXP_EXIT=$?

    END_EXP=$(date +%s)
    echo ""

    if [ $EXP_EXIT -ne 0 ]; then
        echo "  ❌ Esperimenti ${CFG} falliti (exit code $EXP_EXIT) — interrompo."
        exit $EXP_EXIT
    fi
    echo "  ✅ Esperimenti ${CFG} completati in $((END_EXP - START_EXP))s"

    # ── 2. Grafici ───────────────────────────────────────────────────────
    echo ""
    echo "  ════════════════════════════════════════"
    echo "  [${NUM}b] GRAFICI — plot_convergence.py"
    echo "  ════════════════════════════════════════"
    echo ""

    PLOT_EXIT=0
    $APPT plot_convergence.py --results "../${OUTPUT_DIR}/results.json" --imgs "../${IMGS_DIR}" || PLOT_EXIT=$?

    if [ $PLOT_EXIT -ne 0 ]; then
        echo "  ⚠️  Grafici ${CFG} falliti — continuo."
    else
        echo "  ✅ Grafici ${CFG} → ${IMGS_DIR}/"
    fi

    # ── 3. Tabella LaTeX ─────────────────────────────────────────────────
    echo ""
    echo "  ════════════════════════════════════════"
    echo "  [${NUM}c] TABELLA — format_latex.py"
    echo "  ════════════════════════════════════════"
    echo ""

    TABLE_EXIT=0
    $APPT format_latex.py table --results "../${OUTPUT_DIR}/results.json" 2>&1 | tee "$TABLE_FILE" || TABLE_EXIT=${PIPESTATUS[0]}

    echo ""
    if [ $TABLE_EXIT -ne 0 ]; then
        echo "  ⚠️  Tabella ${CFG} fallita."
    else
        echo "  📄 Tabella ${CFG}: ${OUTPUT_DIR}/table.txt"
    fi
    echo ""
done

# ── Config comparison & tabella comparativa (solo se multi-config) ────────────
if [ -z "$CONFIG_ARG" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  CONFIG COMPARISON — summary_config_comparison.png"  ║
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""

    CMP_EXIT=0
    $APPT plot_convergence.py --comparison-only || CMP_EXIT=$?

    if [ $CMP_EXIT -ne 0 ]; then
        echo "  ⚠️  Config comparison fallito (potrebbero servire più config completate)."
    else
        echo "  ✅ Config comparison → docs/report/imgs/summary/summary_config_comparison.png"
    fi

    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║  TABLE COMPARISON — table_comparison.txt"  ║
    echo "╚════════════════════════════════════════════╝"
    echo ""

    TABLE_COMP="$PROJ_DIR/results/table_comparison.txt"
    FMT_EXIT=0
    $APPT format_latex.py comparison --output ../results/table_comparison.txt 2>&1 || FMT_EXIT=$?
    echo ""
    if [ $FMT_EXIT -ne 0 ] || [ ! -f "$TABLE_COMP" ]; then
        echo "  ✅ Tabella comparativa → results/table_comparison.txt"
    else
        echo "  ⚠️  Tabella comparativa fallita."
    fi
fi

# ── Riepilogo ─────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ PIPELINE COMPLETATA — ${TOTAL} config"
echo "  $(date)"
echo "============================================"
echo ""
echo "Output generati:"
if [ -z "$CONFIG_ARG" ]; then
    echo "  docs/report/imgs/summary/summary_config_comparison.png"
    echo "  results/table_comparison.txt"
fi
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
