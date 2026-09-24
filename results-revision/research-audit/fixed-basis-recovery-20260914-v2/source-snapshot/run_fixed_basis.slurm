#!/bin/bash
#SBATCH --job-name=fixed-basis
#SBATCH --output=logs/fixed-basis-%A_%a.out
#SBATCH --error=logs/fixed-basis-%A_%a.err
#SBATCH --partition=ute
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-2
#
# Reviewer objection 3: the conditioning readout is taken along each variant's own
# solve path (its own incumbent, its own basis), so it cannot separate
# representation quality from which vertex that solve reached.  This diagnostic
# holds both fixed: the base model is solved once, its integers fixed, its LP
# solved once for ONE reference basis, and that basis is rebuilt from each
# variant's exported matrix.
#
# Runs inside the gcc13 container (the binary needs its libstdc++).  Unlike the
# timing harness, fixed_basis_diagnostic.py needs numpy, scipy and gurobipy; the
# job checks for them first and aborts with an install hint rather than failing
# deep in.  Submit after the build with --dependency=afterok:<build jobid>.
#
set -euo pipefail

REPO="$HOME/generator-aware-row-scaling"
SIF="$HOME/containers/gcc13.sif"
cd "$REPO"
mkdir -p logs results-revision/fixed-basis
module load singularity 2>/dev/null || true

CLASSES=(
  "entrada-modelo-simple   simple"
  "entrada-SG-Ter-Mer      sgtm"
  "entrada-modelo-completo full"
)
read -r FOLDER TAG <<< "${CLASSES[$SLURM_ARRAY_TASK_ID]}"
THREADS="${SLURM_CPUS_PER_TASK:-16}"

singularity exec --cleanenv -B "$HOME:$HOME" "$SIF" bash -lc "
    set -euo pipefail
    cd '$REPO'
    export GUROBI_HOME=\"\$HOME/solvers/gurobi1301/linux64\"
    export GRB_LICENSE_FILE=\"\$HOME/.gurobi/gurobi.lic\"
    export LD_LIBRARY_PATH=\"\$GUROBI_HOME/lib:\${LD_LIBRARY_PATH:-}\"
    export OMP_NUM_THREADS=$THREADS
    if ! python3 -c 'import numpy, scipy, gurobipy' 2>/dev/null; then
        echo 'Missing numpy/scipy/gurobipy in the container. Install into the user site:' >&2
        echo '  singularity exec \$SIF python3 -m pip install --user numpy scipy gurobipy' >&2
        exit 1
    fi
    python3 scripts/fixed_basis_diagnostic.py \
        --instancias 'data/entradas/$FOLDER'/*.txt \
        --exe code/build/SistemaElectrico \
        --mipgap 0.001 --timelimit 3600 \
        --out '$REPO/results-revision/fixed-basis/${TAG}.csv'
"
echo "done: $TAG"
