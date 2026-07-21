#!/bin/bash
#SBATCH --job-name=flat-cplex
#SBATCH --output=logs/flat-cplex-%A_%a.out
#SBATCH --error=logs/flat-cplex-%A_%a.err
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-3
#
# Reviewer condition: run the role-blind (Flat) controls under CPLEX as well as
# Gurobi, so that the coverage-versus-selectivity ordering can be tested for
# solver dependence instead of being scoped to a single pipeline.
#
# The Simple class at 1% is cheap enough to run on the workstation; this job
# covers the combinations that are not, one array task per class-tolerance
# cell.  Submit with:  sbatch cluster/run_flat_cplex.slurm
#
set -euo pipefail

module purge
module load gurobi cplex singularity 2>/dev/null || true

REPO="${REPO:-$HOME/generator-aware-row-scaling}"
EXE="${EXE:-$REPO/code/build/SistemaElectrico}"
cd "$REPO"
mkdir -p logs results-revision/plano-control-cplex

# class-tolerance cells that need the cluster
CASES=(
  "entrada-SG-Ter-Mer      0.01   sgtm-cplex-1pct"
  "entrada-SG-Ter-Mer      0.001  sgtm-cplex-01pct"
  "entrada-modelo-completo 0.01   full-cplex-1pct"
  "entrada-modelo-completo 0.001  full-cplex-01pct"
)
read -r FOLDER MIPGAP OUTNAME <<< "${CASES[$SLURM_ARRAY_TASK_ID]}"

python3 scripts/validar_preprocesamiento.py \
    "data/entradas/${FOLDER}" \
    --exe "$EXE" \
    --solver Cplex \
    --timeout 3600 \
    --mipgap "$MIPGAP" \
    --variantes estructurado,estructurado_plano,estructurado_matricial,matricial_plano \
    --sin-base \
    --verificar-original \
    --output "results-revision/plano-control-cplex/${OUTNAME}"

echo "done: ${OUTNAME}"
