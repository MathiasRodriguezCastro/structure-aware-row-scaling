#!/bin/bash
#SBATCH --job-name=orf_solver_env
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:15:00

set -euo pipefail
TASK_ROOT=${1:?isolated remote preparation directory required}
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" bash -s -- "$TASK_ROOT" <<'INNER'
set -euo pipefail
TASK_ROOT=$1
python3 "$TASK_ROOT/cluster/install_wheels.py" "$TASK_ROOT"
export PYTHONPATH="$TASK_ROOT/python-deps-v1${PYTHONPATH:+:$PYTHONPATH}"
export LD_PRELOAD="$HOME/solvers/CPLEX_Studio2212/cplex/bin/x86-64_linux/libcplex2212.so"
sha256sum "$LD_PRELOAD" > "$TASK_ROOT/CPLEX_NATIVE.sha256"
python3 "$TASK_ROOT/cluster/preflight.py" "$TASK_ROOT/PREFLIGHT-installed.json"
INNER
