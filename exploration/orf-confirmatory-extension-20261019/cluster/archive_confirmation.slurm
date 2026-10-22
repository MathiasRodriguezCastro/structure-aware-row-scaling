#!/bin/bash
#SBATCH --job-name=orf_evidence_archive
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
set -euo pipefail
TASK_ROOT=${1:?repository root}
ARCHIVE_PATH=${2:?new output archive}
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
  "$HOME/containers/gcc13.sif" python3 \
  "$TASK_ROOT/scripts/research/orf_confirmation_evidence.py" build \
  --root "$TASK_ROOT" --archive "$ARCHIVE_PATH"
