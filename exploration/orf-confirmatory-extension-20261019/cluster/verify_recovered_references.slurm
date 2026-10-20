#!/bin/bash
#SBATCH --job-name=orf_recovery_replay
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00

set -euo pipefail
TASK_ROOT=${1:?isolated repository root required}
singularity exec --cleanenv -B "$HOME:$HOME" -B /clusteruy:/clusteruy \
 "$HOME/containers/gcc13.sif" python3 \
 "$TASK_ROOT/exploration/orf-confirmatory-extension-20261019/verify_recovered_references_stdlib.py"
