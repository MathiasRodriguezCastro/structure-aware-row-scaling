#!/bin/bash
#SBATCH --job-name=flat-cplex
#SBATCH --output=logs/flat-cplex-%A_%a.out
#SBATCH --error=logs/flat-cplex-%A_%a.err
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-5
#
# Reviewer condition: the direct role-blind (Flat) versus selective (SA) controls
# exist under Gurobi only, so the coverage-versus-selectivity ordering cannot be
# told apart from a property of one solver's pipeline.  This runs the same
# controls under CPLEX.
#
# ALL SIX class-by-tolerance cells run here, including Simple.  Simple is cheap
# enough to run on a workstation, but a workstation measurement is not usable:
# the manuscript declares one computational environment in
# tab:computational-environment (ClusterUY, partition ute, Xeon Gold 6138), and
# pooling timings across machines would break exactly the comparability this
# experiment exists to establish.
#
# Submit with:  sbatch cluster/run_flat_cplex.slurm
#
set -euo pipefail

module purge
module load gurobi cplex singularity 2>/dev/null || true

REPO="${REPO:-$HOME/generator-aware-row-scaling}"
EXE="${EXE:-$REPO/code/build/SistemaElectrico}"
cd "$REPO"
mkdir -p logs results-revision/plano-control-cplex

# One task per class-tolerance cell.
CASES=(
  "entrada-modelo-simple   0.01   simple-cplex-1pct"
  "entrada-modelo-simple   0.001  simple-cplex-01pct"
  "entrada-SG-Ter-Mer      0.01   sgtm-cplex-1pct"
  "entrada-SG-Ter-Mer      0.001  sgtm-cplex-01pct"
  "entrada-modelo-completo 0.01   full-cplex-1pct"
  "entrada-modelo-completo 0.001  full-cplex-01pct"
)
read -r FOLDER MIPGAP OUTNAME <<< "${CASES[$SLURM_ARRAY_TASK_ID]}"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"

# The output path must be ABSOLUTE.  The harness launches the binary with
# cwd=code/, so a relative path resolves differently for the binary than for the
# harness: the binary writes its CSVs under code/<path> while the summary looks
# under <path>, and every cell is recorded as ERROR despite having solved
# correctly.  scripts/validar_preprocesamiento.py now resolves this itself, but
# passing an absolute path keeps the job correct with older checkouts too.
python3 scripts/validar_preprocesamiento.py \
    "data/entradas/${FOLDER}" \
    --exe "$EXE" \
    --solver Cplex \
    --timeout 3600 \
    --mipgap "$MIPGAP" \
    --variantes estructurado,estructurado_plano,estructurado_matricial,matricial_plano \
    --sin-base \
    --verificar-original \
    --output "$REPO/results-revision/plano-control-cplex/${OUTNAME}"

echo "done: ${OUTNAME}"
