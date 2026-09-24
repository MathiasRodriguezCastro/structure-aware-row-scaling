#!/bin/bash
#SBATCH --job-name=robust-build
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --account=ute
#SBATCH --constraint=intel
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=1:00:00
#
# Build of the solver-robustness binary (Gurobi + CPLEX + HiGHS) inside the gcc13
# container, from a source tree exported with `git archive`. Usage:
#   sbatch --chdir=$SRC --output=$SRC/logs/build-%j.out cluster/build_robustness.slurm
set -euo pipefail
module load singularity 2>/dev/null || true
SRC="$(pwd)"
SIF="$HOME/containers/gcc13.sif"
mkdir -p logs
singularity exec --cleanenv -B "$HOME:$HOME" "$SIF" bash -lc "
    set -euo pipefail
    cd '$SRC/code'
    export GUROBI_HOME=\"\$HOME/solvers/gurobi1301/linux64\"
    g++ --version | head -1
    rm -rf build-robust
    make BUILD_DIR=build-robust USE_CBC=0 USE_HEXALY=0 USE_HIGHS=1 OPT=-O2 \
         CPLEX_HOME=\"\$HOME/solvers/CPLEX_Studio2212\" HIGHS_HOME=\"\$HOME/solvers/highs-1.15.1\" -j8 2>&1 | tail -3
    sha256sum build-robust/SistemaElectrico | tee build-robust/SHA256
    ldd build-robust/SistemaElectrico | grep -iE 'gurobi|not found' || true
    printf 'configurarSolver --Highs\nsalir\n' | ./build-robust/SistemaElectrico | grep -c \"configurado\"
"
echo "build done"
