#!/bin/bash
#SBATCH --job-name=orf_math_probe
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00

set -euo pipefail
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
TASK_ROOT="$ENV_ROOT/repository"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1:$ENV_ROOT/python-deps-v1/cplex-22.1.2.0.data/purelib"
PROGRAM="$TASK_ROOT/exploration/orf-confirmatory-extension-20261019/cluster/probe_math.py"
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 "$PROGRAM" automatic
export SINGULARITYENV_OPENBLAS_CORETYPE=Haswell
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 "$PROGRAM" Haswell
