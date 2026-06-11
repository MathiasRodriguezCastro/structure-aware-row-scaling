#!/bin/bash
# =============================================================================
# Generic SLURM template — dispatch validation, Cplex (reproduction level N2).
#
# Reproduces ONE scenario (instance class × MIP gap) of the dispatch experiments.
# Edit the parameters below, then submit from the repository root:
#     sbatch cluster/run_validation_cplex.slurm
#
# This is a long run (hours to days; the Full class is the slowest). Submit one
# job per (class × gap). Variants run in every job: base, estructurado (SA-Aug),
# estructurado_matricial (SA-Mat), ruiz (Ruiz), ruiz_columnas (Ruiz+Cols).
# =============================================================================
#SBATCH --job-name=gars_val_cplex
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --partition=YOUR_PARTITION
#SBATCH --time=5-00:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=12G
#SBATCH --output=slurm_%j.out
#SBATCH --error=slurm_%j.err

set -uo pipefail

# ---- parameters to edit -----------------------------------------------------
CLASS=entrada-modelo-simple     # entrada-modelo-simple | entrada-modelo-completo | entrada-SG-Ter-Mer
MIPGAP=0.01                     # 0.01 (1e-2) | 0.001 (1e-3)
TAG=simple-cplex-1pct          # output subfolder name under results/
THREADS=16
# -----------------------------------------------------------------------------

cd "${SLURM_SUBMIT_DIR:-$PWD}" || exit 1
export OMP_NUM_THREADS="$THREADS"

# Point these at your local Cplex install and license. Do NOT commit the license file.
export GUROBI_HOME="${GUROBI_HOME:-$HOME/solvers/cplex1301/linux64}"
export LD_LIBRARY_PATH="$GUROBI_HOME/lib:${LD_LIBRARY_PATH:-}"
# Set your Cplex license via the vendor's environment variable before running.

# Optional: wrap the call in `singularity exec --cleanenv -B "$HOME:$HOME" your.sif bash -lc '...'`
# if the toolchain lives in a container.

OUT="results/$TAG"
mkdir -p "$OUT"

echo "Start: $(date)  Node: $(hostname)  Threads: $THREADS"
python3 scripts/validar_preprocesamiento.py \
    "data/entradas/$CLASS" \
    --exe code/build/SistemaElectrico \
    --solver Cplex \
    --timeout 3600 \
    --mipgap "$MIPGAP" \
    --variantes base,estructurado,estructurado_matricial,ruiz,ruiz_columnas \
    --output "$OUT" \
    --verificar-original \
    2>&1 | tee -a "$OUT/run.out"
echo "End: $(date)"
