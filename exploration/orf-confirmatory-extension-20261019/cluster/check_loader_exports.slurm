#!/bin/bash
#SBATCH --job-name=orf_loader_exports_gate
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:40:00

set -euo pipefail
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
TASK_ROOT="$ENV_ROOT/repository"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_OPENBLAS_CORETYPE=Haswell
export SINGULARITYENV_PYTHONINTMAXSTRDIGITS=0
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
export SINGULARITYENV_GRB_LICENSE_FILE="$HOME/.gurobi/gurobi.lic"
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1:$ENV_ROOT/python-deps-v1/cplex-22.1.2.0.data/purelib"
export SINGULARITYENV_LD_LIBRARY_PATH="$ENV_ROOT/native-cplex-2212"
unset SINGULARITYENV_LD_PRELOAD
SUB=exploration/orf-confirmatory-extension-20261019
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
  "$HOME/containers/gcc13.sif" python3 "$TASK_ROOT/$SUB/check_factor_portability.py" Haswell-library-path-all all
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
  "$HOME/containers/gcc13.sif" python3 "$TASK_ROOT/$SUB/cluster/license_probe.py" "$TASK_ROOT/$SUB/PREFLIGHT-loader-corrected.json"
