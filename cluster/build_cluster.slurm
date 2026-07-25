#!/bin/bash
#SBATCH --job-name=gars-build
#SBATCH --output=logs/gars-build-%j.out
#SBATCH --error=logs/gars-build-%j.err
#SBATCH --partition=ute
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=1:00:00
#
# Clean Gurobi-only build of the solver inside the gcc13 Singularity container,
# for the revision campaigns.  CPLEX and CBC are off (CPLEX is not installed on
# this cluster; CBC is not needed), Hexaly is off.  Submit this first and gate
# the campaign jobs on it with --dependency=afterok:<jobid>.
#
set -euo pipefail

module load singularity 2>/dev/null || true
SIF="$HOME/containers/gcc13.sif"
cd "$HOME/generator-aware-row-scaling"
mkdir -p logs

singularity exec --cleanenv -B "$HOME:$HOME" "$SIF" bash -lc '
    set -euo pipefail
    cd "$HOME/generator-aware-row-scaling/code"
    export GUROBI_HOME="$HOME/solvers/gurobi1301/linux64"
    export GRB_LICENSE_FILE="$HOME/.gurobi/gurobi.lic"
    export LD_LIBRARY_PATH="$GUROBI_HOME/lib:${LD_LIBRARY_PATH:-}"
    g++ --version | head -1
    rm -rf build
    make USE_CPLEX=0 USE_CBC=0 USE_HEXALY=0 OPT=-O2 -j8 2>&1 | tail -4
    echo "=== binary ==="
    ls -lh build/SistemaElectrico
    echo "=== revision flags present? ==="
    strings build/SistemaElectrico | grep -oE "\-\-cubrir-residual|\-\-reportar-duales|\-\-seed" | sort -u
    echo "=== ldd ==="
    ldd build/SistemaElectrico | grep -iE "gurobi|not found" || true
'
echo "build done"
