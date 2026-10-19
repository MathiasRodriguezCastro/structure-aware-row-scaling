#!/bin/bash
#SBATCH --job-name=orf_data_probe
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:15:00

set -euo pipefail
TASK_ROOT=${1:?isolated remote preparation directory required}
SIF="$HOME/containers/gcc13.sif"
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy "$SIF" \
  python3 "$TASK_ROOT/cluster/inventory_remote.py"
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy "$SIF" \
  python3 "$TASK_ROOT/cluster/preflight.py" "$TASK_ROOT/PREFLIGHT-initial.json"
