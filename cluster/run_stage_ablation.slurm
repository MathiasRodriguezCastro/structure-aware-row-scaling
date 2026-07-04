#!/bin/bash
# =============================================================================
# SLURM template — R5: operational stage ablation (local / coupling / full).
#
# Reviewer question (DA-M1, author already acknowledges in the Discussion/Limitations):
# the operational experiments compare the FULL local--block--coupling architecture
# against base / Ruiz, but never run local-only and coupling-only variants on the
# real hydrothermal classes, so the marginal contribution of each stage is not
# attributed. This job runs, in one scenario, the full architecture and its two
# single-stage ablations against the same base, under Gurobi (where the effect lives).
#
#     sbatch cluster/run_stage_ablation.slurm
# =============================================================================
#SBATCH --job-name=gars_r5_ablation
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
MIPGAP=0.01
SOLVER=Gurobi
TAG=simple-gurobi-1pct          # output subfolder under results/r5-ablation/
THREADS=16
TIMEOUT=3600
# -----------------------------------------------------------------------------

cd "${SLURM_SUBMIT_DIR:-$PWD}" || exit 1
export OMP_NUM_THREADS="$THREADS"
export GUROBI_HOME="${GUROBI_HOME:-$HOME/solvers/gurobi1301/linux64}"
export LD_LIBRARY_PATH="$GUROBI_HOME/lib:${LD_LIBRARY_PATH:-}"

EXE=code/build/SistemaElectrico
INPUTS="data/entradas/$CLASS"
OUT="results/r5-ablation/$TAG"
mkdir -p "$OUT"

echo "Start: $(date)  Node: $(hostname)  Class: $CLASS  Solver: $SOLVER"

# full = estructurado (local + coupling); the two single-stage ablations isolate each stage.
# The matrix-only counterparts are included so the SA-Mat attribution can be read too.
# estructurado_plano / matricial_plano: flat control (same per-row kernel on ALL rows,
# no role/block metadata). NOTE: requires a binary rebuilt with the --plano flag
# (rebuild code/ before submitting if the executable predates it).
python3 scripts/validar_preprocesamiento.py "$INPUTS" \
    --exe "$EXE" --solver "$SOLVER" --timeout "$TIMEOUT" --mipgap "$MIPGAP" \
    --output "$OUT" --verificar-original \
    --variantes base,estructurado,estructurado_solo_local,estructurado_solo_acoplamiento,estructurado_matricial,matricial_solo_local,matricial_solo_acoplamiento,estructurado_plano,matricial_plano \
    2>&1 | tee -a "$OUT/run.out"

echo "End: $(date)"
# Analysis: scripts/analisis_tesis_preproc.py reports per-variant sgm/PAR10/Cliff's delta;
# comparing full vs solo_local vs solo_acoplamiento attributes the Gurobi effect to the
# local-row normalization vs the coupling-row treatment. See cluster/README.md (R5).
