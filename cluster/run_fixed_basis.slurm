#!/bin/bash
#SBATCH --job-name=fixed-basis
#SBATCH --output=logs/fixed-basis-%A_%a.out
#SBATCH --error=logs/fixed-basis-%A_%a.err
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --array=0-2
#
# Reviewer objection 3: the conditioning readout reported in the paper is taken
# along each variant's OWN solve path -- its own incumbent, its own final basis --
# so it cannot separate representation quality from the accident of which vertex
# that particular solve reached.
#
# This diagnostic holds both fixed.  The base model is solved once, its integers
# fixed, and its LP solved once to obtain ONE reference basis; that same basis is
# then rebuilt from each variant's exported matrix.  Only the row scaling varies.
#
# The condition numbers themselves are deterministic given a basis, but the basis
# comes from a solve, so this runs on ClusterUY like every other campaign rather
# than on a workstation: the reference basis must come from the same environment
# as the solves the paper reports.
#
# Submit with:  sbatch cluster/run_fixed_basis.slurm
#
set -euo pipefail

module purge
module load gurobi cplex singularity 2>/dev/null || true

REPO="${REPO:-$HOME/generator-aware-row-scaling}"
EXE="${EXE:-$REPO/code/build/SistemaElectrico}"
cd "$REPO"
mkdir -p logs results-revision/fixed-basis

# This script needs numpy, scipy and gurobipy, unlike the timing harness, which
# is standard library only.  The ClusterUY container does not ship them, so fail
# with an actionable message instead of a traceback three hours in.
if ! python3 -c 'import numpy, scipy, gurobipy' 2>/dev/null; then
    echo "Missing Python dependencies for this job (numpy, scipy, gurobipy)." >&2
    echo "Install them into the user site with:" >&2
    echo "  python3 -m pip install --user numpy scipy gurobipy" >&2
    echo "or run this job inside a container that already provides them." >&2
    exit 1
fi

CLASSES=(
  "entrada-modelo-simple   simple"
  "entrada-SG-Ter-Mer      sgtm"
  "entrada-modelo-completo full"
)
read -r FOLDER TAG <<< "${CLASSES[$SLURM_ARRAY_TASK_ID]}"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"

python3 scripts/fixed_basis_diagnostic.py \
    --instancias "data/entradas/${FOLDER}"/*.txt \
    --exe "$EXE" \
    --mipgap 0.001 \
    --timelimit 3600 \
    --out "$REPO/results-revision/fixed-basis/${TAG}.csv"

echo "done: ${TAG}"
