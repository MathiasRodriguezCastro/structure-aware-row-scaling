#!/bin/bash
# =============================================================================
# SLURM template — R3: hyperparameter sensitivity.
#
# Reviewer question (R1 W2, DA-m3): the method fixes the near-identity band u=2,
# K=4 Ruiz iterations, and the coefficient window [1e-9,1e9] without justification.
# Are the results (and the Ruiz "irregularity") robust to these constants, or are
# they artifacts of a particular choice? This job sweeps u, K, and the window on the
# Simple class (cheapest, per the reviewer's "at least on the Simple class") under
# Gurobi, each point in its own tagged folder, all sharing the same 'base'.
#
#     sbatch cluster/run_hyperparam_sensitivity.slurm
# =============================================================================
#SBATCH --job-name=gars_r3_hyper
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
CLASS=entrada-modelo-simple     # Simple is the cheapest; widen later if budget allows.
MIPGAP=0.01
SOLVER=Gurobi
THREADS=16
TIMEOUT=3600
BASEVAR=estructurado            # which generator-aware variant to perturb: estructurado | estructurado_matricial
# -----------------------------------------------------------------------------

cd "${SLURM_SUBMIT_DIR:-$PWD}" || exit 1
export OMP_NUM_THREADS="$THREADS"
export GUROBI_HOME="${GUROBI_HOME:-$HOME/solvers/gurobi1301/linux64}"
export LD_LIBRARY_PATH="$GUROBI_HOME/lib:${LD_LIBRARY_PATH:-}"

EXE=code/build/SistemaElectrico
INPUTS="data/entradas/$CLASS"
ROOT="results/r3-hyperparam/$CLASS-$SOLVER"
mkdir -p "$ROOT"

# extra_prep flags must reach the inner 'preprocesar' line. --banda-identidad sets u;
# --ventana-coef sets the admissible window; --ruiz-iters sets K (only matters for ruiz*
# variants — included here for completeness when BASEVAR is a ruiz variant).
sweep () {  # sweep <out-subdir> <extra-prep...>
    local sub="$1"; shift
    local out="$ROOT/$sub"
    mkdir -p "$out"
    echo ">>> [$sub] extra-prep='$*'  $(date)"
    python3 scripts/validar_preprocesamiento.py "$INPUTS" \
        --exe "$EXE" --solver "$SOLVER" --timeout "$TIMEOUT" --mipgap "$MIPGAP" \
        --output "$out" --verificar-original \
        --variantes "base,$BASEVAR" --extra-prep "$*" \
        2>&1 | tee -a "$out/run.out"
}

echo "Start: $(date)  Node: $(hostname)  variant=$BASEVAR"

# Near-identity band u in {1.5, 2 (default), 4}
sweep u1.5 --banda-identidad 1.5
sweep u2   --banda-identidad 2
sweep u4   --banda-identidad 4

# Ruiz iterations K in {2, 4 (default), 8}  (drives the Ruiz baseline 'irregularity' question)
sweep K2 --ruiz-iters 2
sweep K4 --ruiz-iters 4
sweep K8 --ruiz-iters 8

# Coefficient window in {[1e-6,1e6], [1e-9,1e9] (default), [1e-12,1e12]}
sweep win6  --ventana-coef 1e-6 1e6
sweep win9  --ventana-coef 1e-9 1e9
sweep win12 --ventana-coef 1e-12 1e12

echo "End: $(date)"
# Each subfolder has its own resumen CSV; scripts/analisis_tesis_preproc.py renders the
# per-point sgm/PAR10 so the sensitivity table can be assembled. See cluster/README.md (R3).
