#!/bin/bash
#SBATCH --job-name=orf_confirmation
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00

set -euo pipefail
TASK_ROOT=${1:?isolated repository root required}
STAGE=${2:?gate, run, collect, analyze or seal required}
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_OPENBLAS_CORETYPE=Haswell
export SINGULARITYENV_PYTHONINTMAXSTRDIGITS=0
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
export SINGULARITYENV_GRB_LICENSE_FILE="$HOME/.gurobi/gurobi.lic"
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1:$ENV_ROOT/python-deps-v1/cplex-22.1.2.0.data/purelib"
export SINGULARITYENV_LD_PRELOAD="$ENV_ROOT/native-cplex-2212/libcplex2212.so"
SUB=exploration/orf-confirmatory-extension-20261019
ARGS=()
case "$STAGE" in
  gate) PROGRAM=confirmation_gate.py ;;
  run) PROGRAM=run_confirmation.py; ARGS=(block "$SLURM_ARRAY_TASK_ID") ;;
  collect) PROGRAM=collect_confirmation.py ;;
  analyze) PROGRAM=analyze_confirmation.py ;;
  seal) PROGRAM=seal_confirmation.py ;;
  *) exit 2 ;;
esac
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 "$TASK_ROOT/$SUB/$PROGRAM" "${ARGS[@]}"
