#!/bin/bash
#SBATCH --job-name=seed-repl
#SBATCH --output=logs/seed-repl-%A_%a.out
#SBATCH --error=logs/seed-repl-%A_%a.err
#SBATCH --partition=ute
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-9
#
# Reviewer objection 6: the ~1% effects are of the order of the solver's own
# run-to-run variability, and every published cell was measured once.  This
# replicates the two contrasts that carry the argument -- Simple at 0.1% (the one
# fast-class contrast that survives) and SG-Ter-Mer at 0.1% (where the role-blind
# control wins) -- under five solver seeds each, giving an empirical noise floor
# measured on the same instances and hardware.  Seed 1 is the published seed and
# is included as the reference point.
#
# Runs inside the gcc13 container (the binary needs its newer libstdc++). Submit
# after the build with --dependency=afterok:<build jobid>.
#
set -euo pipefail

REPO="$HOME/generator-aware-row-scaling"
SIF="$HOME/containers/gcc13.sif"
cd "$REPO"
mkdir -p logs results-revision/seed-replication
module load singularity 2>/dev/null || true

SEEDS=(1 2 3 4 5)
CELLS=(
  "entrada-modelo-simple   simple"
  "entrada-SG-Ter-Mer      sgtm"
)
SEED="${SEEDS[$(( SLURM_ARRAY_TASK_ID % 5 ))]}"
read -r FOLDER TAG <<< "${CELLS[$(( SLURM_ARRAY_TASK_ID / 5 ))]}"
THREADS="${SLURM_CPUS_PER_TASK:-16}"

singularity exec --cleanenv -B "$HOME:$HOME" "$SIF" bash -lc "
    set -euo pipefail
    cd '$REPO'
    export GUROBI_HOME=\"\$HOME/solvers/gurobi1301/linux64\"
    export GRB_LICENSE_FILE=\"\$HOME/.gurobi/gurobi.lic\"
    export LD_LIBRARY_PATH=\"\$GUROBI_HOME/lib:\${LD_LIBRARY_PATH:-}\"
    export OMP_NUM_THREADS=$THREADS
    python3 scripts/validar_preprocesamiento.py \
        'data/entradas/$FOLDER' \
        --exe code/build/SistemaElectrico \
        --solver Gurobi --timeout 3600 --mipgap 0.001 --seed $SEED \
        --variantes base,estructurado,estructurado_plano,estructurado_matricial,matricial_plano \
        --verificar-original \
        --output '$REPO/results-revision/seed-replication/${TAG}-01pct-seed${SEED}'
"
echo "done: ${TAG} seed=${SEED}"
