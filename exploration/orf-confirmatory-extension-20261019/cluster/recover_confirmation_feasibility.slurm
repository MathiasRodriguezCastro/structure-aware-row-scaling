#!/bin/bash
#SBATCH --job-name=orf_reference_feasibility
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:20:00

set -euo pipefail
TASK_ROOT=${1:?isolated repository root required}
STAGE=${2:?worker or collect required}
ENV_ROOT="$HOME/row-scaling-orf-extension-20261019"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_OPENBLAS_CORETYPE=Haswell
export SINGULARITYENV_PYTHONINTMAXSTRDIGITS=0
export SINGULARITYENV_PYTHONPATH="$ENV_ROOT/python-deps-v1"
ARGS=("$STAGE")
if [[ "$STAGE" == worker ]]; then
  ARGS+=(--index "$SLURM_ARRAY_TASK_ID")
fi
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 \
 "$TASK_ROOT/exploration/orf-confirmatory-extension-20261019/recover_confirmation_feasibility.py" "${ARGS[@]}"
