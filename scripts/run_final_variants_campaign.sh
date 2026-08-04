#!/usr/bin/env bash
# Small, decisive operational campaign for the four final attribution variants:
#   Base / Flat-GM (matricial_plano) / Flat-L2 (matricial_plano_l2) / Role-Hybrid (role_hybrid).
# Design: 2 families (Simple, SG-Ter-Mer) x 2 solvers (Gurobi, CPLEX) x 2 gaps (1%, 0.1%),
# fixed seed, fixed timeout, same coverage/bands/safeguards. Deterministic instance subsets.
set -u
cd "$(dirname "$0")/.."
export GRB_LICENSE_FILE=${GRB_LICENSE_FILE:-/home/mathiasr/gurobi.lic}

EXE=code/build/SistemaElectrico
TIMEOUT=${TIMEOUT:-60}
SEED=${SEED:-42}
VARIANTS="base,matricial_plano,matricial_plano_l2,role_hybrid"
OUT=results-revision/final-variants
SIMPLE=$(tr '\n' ' ' < $OUT/instances_simple.txt)
SGTM=$(tr '\n' ' ' < $OUT/instances_sgtm.txt)

run() {  # $1 solver  $2 gap  $3 gaptag  $4 famtag  $5 instances
  local solver=$1 gap=$2 gaptag=$3 fam=$4; shift 4
  local odir=$OUT/${solver}_${gaptag}_${fam}
  echo "=== $solver gap=$gap ($gaptag) family=$fam -> $odir ==="
  python3 scripts/validar_preprocesamiento.py $@ \
    --exe $EXE --solver $solver --timeout $TIMEOUT --mipgap $gap --seed $SEED \
    --variantes $VARIANTS --verificar-original --output $odir
}

for solver in Gurobi Cplex; do
  for pair in "0.01 1pct" "0.001 01pct"; do
    set -- $pair; gap=$1; gaptag=$2
    run $solver $gap $gaptag simple $SIMPLE
    run $solver $gap $gaptag sgtm   $SGTM
  done
done
echo "ALL DONE"
