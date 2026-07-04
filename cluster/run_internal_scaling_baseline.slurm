#!/bin/bash
# =============================================================================
# SLURM template — R1: solver-internal-scaling baseline.
#
# Reviewer question (EIC W2, R1 W1, R2 W3, DA-M1): is the generator-aware gain
# just "any extra scaling pass", which the solver could have produced itself?
# This job runs the UNSCALED model (base) under the solver's OWN scaling options
# and compares it, in the same scenario, against the generator-aware variants run
# under default internal scaling. If a tuned internal ScaleFlag matches SA-Aug/SA-Mat,
# the distinctive claim deflates; if it does not, the claim is isolated.
#
# Submit one job per (class x gap x solver). Edit the parameters, then:
#     sbatch cluster/run_internal_scaling_baseline.slurm
# =============================================================================
#SBATCH --job-name=gars_r1_intscale
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
SOLVER=Gurobi                   # Gurobi | Cplex
TAG=simple-gurobi-1pct          # output subfolder name under results/r1-internal-scaling/
THREADS=16
TIMEOUT=3600
# -----------------------------------------------------------------------------

cd "${SLURM_SUBMIT_DIR:-$PWD}" || exit 1
export OMP_NUM_THREADS="$THREADS"
export GUROBI_HOME="${GUROBI_HOME:-$HOME/solvers/gurobi1301/linux64}"
export LD_LIBRARY_PATH="$GUROBI_HOME/lib:${LD_LIBRARY_PATH:-}"
# Set the Gurobi / CPLEX license via the vendor environment variables before running.
# Optional: wrap the python call in `singularity exec --cleanenv -B "$HOME:$HOME" your.sif bash -lc '...'`.

EXE=code/build/SistemaElectrico
INPUTS="data/entradas/$CLASS"
ROOT="results/r1-internal-scaling/$TAG"
mkdir -p "$ROOT"

run () {  # run <out-subdir> <validar-args...>
    local sub="$1"; shift
    local out="$ROOT/$sub"
    mkdir -p "$out"
    echo ">>> [$sub] $(date)"
    python3 scripts/validar_preprocesamiento.py "$INPUTS" \
        --exe "$EXE" --solver "$SOLVER" --timeout "$TIMEOUT" --mipgap "$MIPGAP" \
        --output "$out" --verificar-original "$@" \
        2>&1 | tee -a "$out/run.out"
}

echo "Start: $(date)  Node: $(hostname)  Solver: $SOLVER  Threads: $THREADS"

# (a) Reference: generator-aware variants under DEFAULT internal scaling (no --scaleflag).
run aware-default --variantes base,estructurado,estructurado_matricial,ruiz,ruiz_columnas

# (b) Baseline: UNSCALED model under each solver-internal scaling option.
#     --sin-base + --variantes base re-runs ONLY the base model, now with the
#     solver's own scaling knob set. Each setting lands in its own folder so the
#     analysis can pair it against the same instances in (a).
if [ "$SOLVER" = "Gurobi" ]; then
    for SF in 0 1 2 3; do
        run "base-scaleflag$SF" --sin-base --variantes base --scaleflag "$SF"
    done
else  # Cplex Read::Scale in {-1 (none), 0 (default eq.), 1 (aggressive)}
    for CS in -1 0 1; do
        run "base-cplexscale${CS/-/m}" --sin-base --variantes base --cplexscale "$CS"
    done
fi

echo "End: $(date)"
# Analysis: scripts/analisis_tesis_preproc.py compares the per-instance solver time of
# 'base' across (a) default vs (b) each internal-scaling setting, against estructurado /
# estructurado_matricial. See cluster/README.md (section R1).
