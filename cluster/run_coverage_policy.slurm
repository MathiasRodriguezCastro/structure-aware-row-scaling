#!/bin/bash
#SBATCH --job-name=coverage-r1
#SBATCH --output=logs/coverage-r1-%A_%a.out
#SBATCH --error=logs/coverage-r1-%A_%a.err
#SBATCH --partition=ute
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-5
#
# Reviewer R1 / R2-W1 / DA-C1 (the decisive required item): the missing THIRD arm
# of the coverage-versus-selectivity comparison.  Six variants per cell on matched
# pairs -- selective (estructurado / estructurado_matricial), metadata-routed full
# coverage (estructurado_full / matricial_full, the new SA-*-Full arm), and
# role-blind Flat (estructurado_plano / matricial_plano) -- Gurobi, all six
# class-tolerance cells, on ClusterUY partition ute for comparability with the
# published campaign.
#
# The solver binary is built inside the gcc13 container (build_cluster.slurm) and
# links a newer libstdc++/glibc than the compute-node base OS, so the run must
# execute INSIDE the container too.  Submit after the build:
#   BUILD=$(sbatch --parsable cluster/build_cluster.slurm)
#   sbatch --dependency=afterok:$BUILD cluster/run_coverage_policy.slurm
#
set -euo pipefail

REPO="$HOME/generator-aware-row-scaling"
SIF="$HOME/containers/gcc13.sif"
cd "$REPO"
mkdir -p logs results-revision/coverage-policy
module load singularity 2>/dev/null || true

CASES=(
  "entrada-modelo-simple   0.01   simple-1pct"
  "entrada-modelo-simple   0.001  simple-01pct"
  "entrada-SG-Ter-Mer      0.01   sgtm-1pct"
  "entrada-SG-Ter-Mer      0.001  sgtm-01pct"
  "entrada-modelo-completo 0.01   full-1pct"
  "entrada-modelo-completo 0.001  full-01pct"
)
read -r FOLDER MIPGAP OUTNAME <<< "${CASES[$SLURM_ARRAY_TASK_ID]}"
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
        --solver Gurobi --timeout 3600 --mipgap $MIPGAP \
        --variantes estructurado,estructurado_full,estructurado_plano,estructurado_matricial,matricial_full,matricial_plano \
        --sin-base --verificar-original \
        --output '$REPO/results-revision/coverage-policy/$OUTNAME'
"
echo "done: $OUTNAME"
