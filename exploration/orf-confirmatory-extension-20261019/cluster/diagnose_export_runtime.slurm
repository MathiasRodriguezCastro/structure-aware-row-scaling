#!/bin/bash
#SBATCH --job-name=orf_export_loader_probe
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00

set -euo pipefail
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
TASK_ROOT="$ENV_ROOT/repository"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_OPENBLAS_CORETYPE=Haswell
export SINGULARITYENV_PYTHONINTMAXSTRDIGITS=0
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1:$ENV_ROOT/python-deps-v1/cplex-22.1.2.0.data/purelib"
PROGRAM="$TASK_ROOT/exploration/orf-confirmatory-extension-20261019/diagnose_export_runtime.py"
for MODE in preloaded none library-path late-global; do
  unset SINGULARITYENV_LD_PRELOAD SINGULARITYENV_LD_LIBRARY_PATH
  if [[ "$MODE" == preloaded ]]; then
    export SINGULARITYENV_LD_PRELOAD="$ENV_ROOT/native-cplex-2212/libcplex2212.so"
  elif [[ "$MODE" == library-path ]]; then
    export SINGULARITYENV_LD_LIBRARY_PATH="$ENV_ROOT/native-cplex-2212"
  fi
  singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
    "$HOME/containers/gcc13.sif" python3 "$PROGRAM" "$MODE"
done
