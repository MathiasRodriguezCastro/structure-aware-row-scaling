#!/bin/bash
#SBATCH --job-name=orf_deploy_gate
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00

set -euo pipefail
TASK_ROOT=${1:?isolated repository root required}
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1:$ENV_ROOT/python-deps-v1/cplex-22.1.2.0.data/purelib"
export SINGULARITYENV_LD_PRELOAD="$ENV_ROOT/native-cplex-2212/libcplex2212.so"
SUB=exploration/orf-confirmatory-extension-20261019
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 "$TASK_ROOT/$SUB/deployment_check.py"
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 "$TASK_ROOT/$SUB/test_native.py"
