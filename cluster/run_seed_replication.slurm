#!/bin/bash
#SBATCH --job-name=seed-repl
#SBATCH --output=logs/seed-repl-%A_%a.out
#SBATCH --error=logs/seed-repl-%A_%a.err
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-9
#
# Reviewer objection 6: the reported effects are of order 1%, run-to-run MIP
# variability may be of the same order, and every published cell was measured
# with a single run.  Without a replication the two cannot be separated.
#
# This job replicates the two contrasts that carry the argument, each under five
# solver seeds, so the paired SA-versus-Flat effect can be compared against an
# empirical noise floor measured on the same instances and the same hardware:
#
#   Simple      at 0.1%  -- the ONE fast-class contrast that survives the
#                           release-build reanalysis (SA-Aug, q6=0.010, ~0.9%)
#   SG-Ter-Mer  at 0.1%  -- the contrast where the role-blind control wins
#
# Seed 1 is the seed used for every published result, so it is included as the
# reference point rather than as an extra condition.  Without --seed the binary
# still uses seed 1, so this changes nothing about previously reported runs.
#
# Submit with:  sbatch cluster/run_seed_replication.slurm
#
set -euo pipefail

module purge
module load gurobi cplex singularity 2>/dev/null || true

REPO="${REPO:-$HOME/generator-aware-row-scaling}"
EXE="${EXE:-$REPO/code/build/SistemaElectrico}"
cd "$REPO"
mkdir -p logs results-revision/seed-replication

# 5 seeds x 2 class cells = 10 array tasks
SEEDS=(1 2 3 4 5)
CELLS=(
  "entrada-modelo-simple   simple"
  "entrada-SG-Ter-Mer      sgtm"
)

SEED_IDX=$(( SLURM_ARRAY_TASK_ID % 5 ))
CELL_IDX=$(( SLURM_ARRAY_TASK_ID / 5 ))
SEED="${SEEDS[$SEED_IDX]}"
read -r FOLDER TAG <<< "${CELLS[$CELL_IDX]}"

# Pinning matters: the effect under test is ~1%, so a migrating process would add
# noise of the same order as the signal we are trying to measure.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"

python3 scripts/validar_preprocesamiento.py \
    "data/entradas/${FOLDER}" \
    --exe "$EXE" \
    --solver Gurobi \
    --timeout 3600 \
    --mipgap 0.001 \
    --seed "$SEED" \
    --variantes base,estructurado,estructurado_plano,estructurado_matricial,matricial_plano \
    --verificar-original \
    --output "results-revision/seed-replication/${TAG}-01pct-seed${SEED}"

echo "done: ${TAG} seed=${SEED}"
