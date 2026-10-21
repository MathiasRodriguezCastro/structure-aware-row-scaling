#!/bin/bash
#SBATCH --job-name=orf_analysis_verify
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00

set -euo pipefail
TASK_ROOT=${1:?isolated repository root required}
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
export SINGULARITYENV_OPENBLAS_CORETYPE=Haswell
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_PYTHONINTMAXSTRDIGITS=0
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1"
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 \
 "$TASK_ROOT/exploration/orf-confirmatory-extension-20261019/verify_confirmation_analysis.py"
