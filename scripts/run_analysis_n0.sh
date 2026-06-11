#!/usr/bin/env bash
# Reproduction level N0: rebuild all paper tables/figures from results/*/resumen.csv
# (no solver needed). Outputs go to results-analysis/.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=results-analysis
A=scripts/analisis_tesis_preproc.py
run () {  # $1=simple-dir $2=full-dir $3=sg-dir $4=output-tag
  python3 "$A" \
    --grupo "Simple=results/$1" \
    --grupo "Full=results/$2" \
    --grupo "SG-Ter-Mer=results/$3" \
    --timeout 3600 --output "$OUT/$4"
}
run validacion-preproc-simple                  validacion-preproc-completo                  validacion-preproc-sg-ter-mer                  esc1-gurobi-1pct
run validacion-preproc-simple-gap0001          validacion-preproc-completo-gap0001          validacion-preproc-sg-ter-mer-gap0001          esc2-gurobi-01pct
run validacion-preproc-simple-cplex-ute        validacion-preproc-completo-cplex-ute        validacion-preproc-sg-ter-mer-cplex-ute        esc3-cplex-1pct
run validacion-preproc-simple-cplex-ute-gap0001 validacion-preproc-completo-cplex-ute-gap0001 validacion-preproc-sg-ter-mer-cplex-ute-gap0001 esc4-cplex-01pct
echo "N0 analysis written under $OUT/"
