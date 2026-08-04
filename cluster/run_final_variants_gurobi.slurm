#!/bin/bash
#SBATCH --job-name=gars-final-gur
#SBATCH --output=logs/gars-final-gur-%A_%a.out
#SBATCH --error=logs/gars-final-gur-%A_%a.err
#SBATCH --partition=ute
#SBATCH --cpus-per-task=16
#SBATCH --mem=16G
#SBATCH --time=1-00:00:00
#SBATCH --array=0-3
#
# Small, decisive operational campaign — Gurobi arm — for the four final attribution
# variants: Base / Flat-GM (matricial_plano) / Flat-L2 (matricial_plano_l2) /
# Role-Hybrid (role_hybrid). One array task per (family x gap). Deterministic 15+15
# instance subsets, fixed seed, same coverage/bands/clip/safeguards, original-scale
# verification on. CPLEX arm is separate (CPLEX is not on this cluster).
#
# Submit gated on the build:
#   B=$(sbatch --parsable cluster/build_cluster.slurm)
#   sbatch --dependency=afterok:$B cluster/run_final_variants_gurobi.slurm
set -uo pipefail

module load singularity 2>/dev/null || true
SIF="$HOME/containers/gcc13.sif"
REPO="$HOME/generator-aware-row-scaling"
cd "$REPO"
mkdir -p logs

TIMEOUT=${TIMEOUT:-1800}
SEED=${SEED:-42}
VARIANTS="base,matricial_plano,matricial_plano_l2,role_hybrid"

CASES=(
  "simple 0.01  1pct"
  "simple 0.001 01pct"
  "sgtm   0.01  1pct"
  "sgtm   0.001 01pct"
)
read -r FAM MIPGAP GAPTAG <<< "${CASES[$SLURM_ARRAY_TASK_ID]}"
INSTANCES=$(tr '\n' ' ' < "results-revision/final-variants/instances_${FAM}.txt")
OUT="$REPO/results-revision/final-variants/gurobi_${FAM}_${GAPTAG}"
mkdir -p "$OUT"

echo "Start: $(date)  Node: $(hostname)  cell=${FAM}/${GAPTAG}  gap=${MIPGAP}  timeout=${TIMEOUT}"

singularity exec --cleanenv -B "$HOME:$HOME" "$SIF" bash -lc "
    set -uo pipefail
    cd '$REPO'
    export GUROBI_HOME='$HOME/solvers/gurobi1301/linux64'
    export GRB_LICENSE_FILE='$HOME/.gurobi/gurobi.lic'
    export LD_LIBRARY_PATH=\"\$GUROBI_HOME/lib:\${LD_LIBRARY_PATH:-}\"
    export OMP_NUM_THREADS='${SLURM_CPUS_PER_TASK:-16}'
    python3 scripts/validar_preprocesamiento.py $INSTANCES \
        --exe '$REPO/code/build/SistemaElectrico' \
        --solver Gurobi --timeout $TIMEOUT --mipgap $MIPGAP --seed $SEED \
        --variantes $VARIANTS --verificar-original --output '$OUT'
"
echo "End: $(date)  cell=${FAM}/${GAPTAG}"
