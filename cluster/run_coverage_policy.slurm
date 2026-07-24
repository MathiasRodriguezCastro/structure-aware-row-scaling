#!/bin/bash
#SBATCH --job-name=coverage-r1
#SBATCH --output=logs/coverage-r1-%A_%a.out
#SBATCH --error=logs/coverage-r1-%A_%a.err
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-5
#
# Reviewer R1 / R2-W1 / DA-C1 (the decisive required item): the paper compared
# the most selective R_other policy (leave unscaled) against the opposite extreme
# (role-blind full coverage), so it tested "don't scale the worst rows" versus
# "scale everything," not selectivity versus coverage.  This runs the missing
# THIRD arm -- metadata-driven full coverage (SA-*-Full: --cubrir-residual) --
# alongside the selective rule and the role-blind Flat control, on matched pairs.
#
# Three arms per kernel, both kernels, so each cell compares:
#   selective        estructurado / matricial
#   metadata-routed  estructurado_full / matricial_full   <-- the new arm
#   role-blind Flat  estructurado_plano / matricial_plano
#
# Gurobi only (R1 is scoped to Gurobi).  One array task per class-tolerance cell.
# Runs on ClusterUY so the timing is comparable to the declared environment.
#
# Requires the binary rebuilt with --cubrir-residual:
#   make -f cluster/Makefile.cluster
#
# Submit with:  sbatch cluster/run_coverage_policy.slurm
#
set -euo pipefail

module purge
module load gurobi cplex singularity 2>/dev/null || true

REPO="${REPO:-$HOME/generator-aware-row-scaling}"
EXE="${EXE:-$REPO/code/build/SistemaElectrico}"
cd "$REPO"
mkdir -p logs results-revision/coverage-policy

CASES=(
  "entrada-modelo-simple   0.01   simple-1pct"
  "entrada-modelo-simple   0.001  simple-01pct"
  "entrada-SG-Ter-Mer      0.01   sgtm-1pct"
  "entrada-SG-Ter-Mer      0.001  sgtm-01pct"
  "entrada-modelo-completo 0.01   full-1pct"
  "entrada-modelo-completo 0.001  full-01pct"
)
read -r FOLDER MIPGAP OUTNAME <<< "${CASES[$SLURM_ARRAY_TASK_ID]}"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"

# Absolute output path: the harness launches the binary with cwd=code/, so a
# relative path would misfile the CSVs and every cell would read as ERROR.
python3 scripts/validar_preprocesamiento.py \
    "data/entradas/${FOLDER}" \
    --exe "$EXE" \
    --solver Gurobi \
    --timeout 3600 \
    --mipgap "$MIPGAP" \
    --variantes estructurado,estructurado_full,estructurado_plano,estructurado_matricial,matricial_full,matricial_plano \
    --sin-base \
    --verificar-original \
    --output "$REPO/results-revision/coverage-policy/${OUTNAME}"

echo "done: ${OUTNAME}"
