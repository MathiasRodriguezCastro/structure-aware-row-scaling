#!/bin/bash
#SBATCH --job-name=orf_env_final
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00

set -euo pipefail
TASK_ROOT=${1:?isolated environment directory required}
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
# The IBM wheel places its Python package in the wheel's purelib scheme.
export SINGULARITYENV_PYTHONPATH="$TASK_ROOT/python-deps-v1:$TASK_ROOT/python-deps-v1/cplex-22.1.2.0.data/purelib"
export SINGULARITYENV_LD_PRELOAD="$TASK_ROOT/native-cplex-2212/libcplex2212.so"
singularity exec --cleanenv -B "$HOME:$HOME" "$HOME/containers/gcc13.sif" \
 python3 "$TASK_ROOT/cluster/preflight.py" "$TASK_ROOT/PREFLIGHT-final.json"
