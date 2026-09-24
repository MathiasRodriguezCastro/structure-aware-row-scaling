#!/bin/bash
# Submit one run table as a SLURM array.
#   cluster/submit_robustness.sh <table.csv> <throttle> [--dependency=...]
# Run from the exported source tree. Gurobi tables must use throttle 2 (WLS sessions).
set -euo pipefail
TABLE="$1"; THROTTLE="$2"; shift 2
SRC="$(pwd)"
NAME="$(basename "$TABLE" .csv)"
STAGE="${NAME%%-*}"
OUT="$HOME/gars-robust/runs/$STAGE/${NAME#*-}"
MANIFEST="$SRC/results-revision/solver-robustness/campaign-manifest.json"
MANIFEST_SHA256="$(sha256sum "$MANIFEST" | cut -d' ' -f1)"
read -r NSHARDS MAXCAP NRUNS < <(awk -F, 'NR>1 {s[$3]+=$13; n[$3]++} END {m=0; for (k in s) {c++; if (s[k]+900*n[k]>m) m=s[k]+900*n[k]}; print c, m, NR-1}' "$TABLE")
HOURS=$(( (MAXCAP + 3599) / 3600 + 1 ))
mkdir -p "$OUT" "$SRC/logs"
echo "$NAME: $NRUNS runs, $NSHARDS shards, time ${HOURS}h, throttle %$THROTTLE -> $OUT"
sbatch --parsable --job-name="r-$NAME" --array="0-$((NSHARDS - 1))%$THROTTLE" --time="${HOURS}:00:00" \
    --chdir="$SRC" --output="$SRC/logs/$NAME-%A_%a.out" \
    --export=ALL,RUNS="$SRC/$TABLE",OUT="$OUT",CAMPAIGN_ID="solver-robustness-v1",MANIFEST_SHA256="$MANIFEST_SHA256" \
    "$@" cluster/run_robustness.slurm
