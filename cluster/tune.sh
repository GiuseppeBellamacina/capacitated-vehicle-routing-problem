#!/bin/bash
# ============================================================================
# SLURM batch script — CVRP Optuna Hyperparameter Tuning
#
# Esegue il tuning automatico dei parametri HGA con Optuna, poi salva
# il miglior config trovato come YAML pronto per run_experiments.py.
#
# Uso:
#   sbatch cluster/tune.sh                     # usa config/config_optuna.yaml
#   sbatch cluster/tune.sh config_optuna_v2    # usa config/config_optuna_v2.yaml
#
#   Con sbatch, l'argomento va DOPO lo script:
#     sbatch cluster/tune.sh config_optuna_v2
#   In locale (test):
#     bash cluster/tune.sh config_optuna_v2
# ============================================================================

#SBATCH --job-name=cvrp-tune
#SBATCH --account=thesis-course
#SBATCH --partition=thesis-course
#SBATCH --qos=gpu-xlarge
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1 --gres=shard:22528
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=bellamacina50@gmail.com
#SBATCH --output=logs/slurm-tune-%j.log

set -e -o pipefail

PROJ_DIR="$HOME/capacitated-vehicle-routing-problem"
CONFIG_NAME="${1:-config_optuna}"   # nome config senza .yaml (default: config_optuna)

CFG_FILE="$PROJ_DIR/config/${CONFIG_NAME}.yaml"

echo "============================================"
echo "  CVRP Optuna Tuning"
echo "  Config:    ${CONFIG_NAME}"
echo "  Job ID:    ${SLURM_JOB_ID}"
echo "  Node:      $(hostname)"
echo "  Date:      $(date)"
echo "============================================"
echo ""

if [ ! -f "$CFG_FILE" ]; then
    echo "Errore: file '$CFG_FILE' non trovato."
    echo "Config Optuna disponibili:"
    ls -1 "$PROJ_DIR"/config/config_optuna*.yaml 2>/dev/null | sed 's/.*\///; s/\.yaml//' || echo "  (nessuno)"
    exit 1
fi

cd "$PROJ_DIR/backend"

# ── Legge parametri dal config YAML per il reporting ────────────────────────
TRIALS=$(grep '^trials:' "$CFG_FILE" | awk '{print $2}')
BUDGET=$(grep '^budget:' "$CFG_FILE" | awk '{print $2}')
STORAGE=$(grep '^storage:' "$CFG_FILE" | awk '{print $2}')
OUTPUT_CONFIG=$(grep '^output_config:' "$CFG_FILE" | awk '{print $2}')

echo "  Trials:       ${TRIALS}"
echo "  Budget/trial: ${BUDGET}"
echo "  Storage:      ${STORAGE}"
if [ -n "$OUTPUT_CONFIG" ]; then
    echo "  Output:       ${OUTPUT_CONFIG}"
fi
echo ""

# ── Crea directory output (prima che Python le crei) ─────────────────────────
mkdir -p "$PROJ_DIR/logs"
mkdir -p "$PROJ_DIR/config"
mkdir -p "$PROJ_DIR/results/tuning"

APPT="apptainer run /shared/sifs/latest.sif python3"

# ── Tuning Optuna ────────────────────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  OPTUNA TUNING — tune_parameters.py"
echo "════════════════════════════════════════"
echo ""

START_TUNE=$(date +%s)

TUNE_EXIT=0
$APPT tune_parameters.py --config "../config/${CONFIG_NAME}.yaml" || TUNE_EXIT=$?

END_TUNE=$(date +%s)
ELAPSED=$((END_TUNE - START_TUNE))

echo ""

if [ $TUNE_EXIT -ne 0 ]; then
    echo "  ❌ Tuning fallito (exit code $TUNE_EXIT)."
    exit $TUNE_EXIT
fi

echo "  ⏱️  Tuning completato in ${ELAPSED}s ($((ELAPSED / 60)) min)"

# ── Verifica output ──────────────────────────────────────────────────────────
if [ -n "$OUTPUT_CONFIG" ] && [ -f "$PROJ_DIR/$OUTPUT_CONFIG" ]; then
    echo "  ✅ Best config salvato → ${OUTPUT_CONFIG}"

    # Copia anche in results/tuning/ per centralizzare gli output
    mkdir -p "$PROJ_DIR/results/tuning"
    cp "$PROJ_DIR/$OUTPUT_CONFIG" "$PROJ_DIR/results/tuning/$(basename "$OUTPUT_CONFIG")"
    echo "  📋 Copia locale  → results/tuning/$(basename "$OUTPUT_CONFIG")"

    echo ""
    echo "  Per eseguire esperimenti con questo config:"
    echo "    sbatch cluster/run.sh $(basename "$OUTPUT_CONFIG" .yaml)"
elif [ -n "$OUTPUT_CONFIG" ]; then
    echo "  ⚠️  Output config '${OUTPUT_CONFIG}' non trovato — il tuning potrebbe non aver completato alcun trial."
fi

if [ -f "$PROJ_DIR/results/tuning/tuning_summary.json" ]; then
    echo "  ✅ Tuning summary → results/tuning/tuning_summary.json"
fi

echo ""
echo "============================================"
echo "  ✅ OPTUNA TUNING COMPLETATO"
echo "  $(date)"
echo "============================================"

exit 0
