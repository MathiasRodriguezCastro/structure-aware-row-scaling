#!/bin/bash
#SBATCH --job-name=robust-run
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --account=ute
#SBATCH --constraint=intel
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#
# One shard of a frozen robustness run table (single-thread solves; two cores are
# reserved per task to limit contention). Submitted by cluster/submit_robustness.sh,
# which sets RUNS, OUT, CAMPAIGN_ID, MANIFEST_SHA256 and the array/throttle/time.
set -uo pipefail
module load singularity 2>/dev/null || true
SRC="$(pwd)"
SIF="$HOME/containers/gcc13.sif"
: "${RUNS:?}" "${OUT:?}" "${CAMPAIGN_ID:?}" "${MANIFEST_SHA256:?}"
GIT_COMMIT="$(cat "$SRC/COMMIT")"
BINARY_SHA256="$(cut -d' ' -f1 "$SRC/code/build-robust/SHA256")"
echo "start $(date -u +%FT%TZ) node=$(hostname) shard=$SLURM_ARRAY_TASK_ID runs=$RUNS"
singularity exec --cleanenv -B "$HOME:$HOME" "$SIF" bash -lc "
    set -uo pipefail
    cd '$SRC'
    export GUROBI_HOME=\"\$HOME/solvers/gurobi1301/linux64\"
    export GRB_LICENSE_FILE=\"\$HOME/.gurobi/gurobi.lic\"
    export LD_LIBRARY_PATH=\"\$GUROBI_HOME/lib:\${LD_LIBRARY_PATH:-}\"
    export PYTHONDONTWRITEBYTECODE=1 SLURM_JOB_ID='$SLURM_JOB_ID' SLURM_ARRAY_TASK_ID='$SLURM_ARRAY_TASK_ID'
    python3 scripts/research/robustness_runner.py --runs '$RUNS' --shard '$SLURM_ARRAY_TASK_ID' \
        --out '$OUT' --exe code/build-robust/SistemaElectrico --campaign-id '$CAMPAIGN_ID' \
        --manifest-sha256 '$MANIFEST_SHA256' --git-commit '$GIT_COMMIT' --binary-sha256 '$BINARY_SHA256'
"
echo "end $(date -u +%FT%TZ) rc=$?"
