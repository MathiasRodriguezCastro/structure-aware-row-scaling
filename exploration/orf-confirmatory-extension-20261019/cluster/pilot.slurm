#!/bin/bash
#SBATCH --job-name=orf_pilot
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:45:00

# No explicit memory guess: the site's 2048 MiB/CPU default is profiled.
set -euo pipefail
TASK_ROOT=${1:?isolated repository root required}
STAGE=${2:?references or pilot required}
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
export SINGULARITYENV_GRB_LICENSE_FILE="$HOME/.gurobi/gurobi.lic"
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1:$ENV_ROOT/python-deps-v1/cplex-22.1.2.0.data/purelib"
export SINGULARITYENV_LD_PRELOAD="$ENV_ROOT/native-cplex-2212/libcplex2212.so"
SUB=exploration/orf-confirmatory-extension-20261019
if [[ "$STAGE" == references ]]; then
  PROGRAM=references.py
  ARGS=("$SLURM_ARRAY_TASK_ID")
elif [[ "$STAGE" == pilot ]]; then
  PROGRAM=runner.py
  ARGS=(block "$SLURM_ARRAY_TASK_ID")
else
  exit 2
fi
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 "$TASK_ROOT/$SUB/$PROGRAM" "${ARGS[@]}"
