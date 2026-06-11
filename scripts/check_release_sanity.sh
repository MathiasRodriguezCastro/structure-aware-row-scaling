#!/usr/bin/env bash
# =============================================================================
# Pre-release sanity checks for the reproducibility repository.
#
# Hard-fails (exit 1) on:
#   (1) leaked private paths / cluster SSH host / mail-user directives;
#   (2) high-signal credentials or committed license/key files;
#   (3) any residual LSTM / Dantzig-Wolfe / column-generation symbol under code/.
#
# Emails are only *listed* for manual review (not a hard fail): the author's
# published contact email is expected in paper/ and CITATION.cff. The bare user
# name and the public "cluster.uy" project URL (paper acknowledgment) are NOT
# flagged; only the private home path and the SSH login host are.
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2          # repository root
SELF="check_release_sanity.sh"
EXC=(--exclude-dir=.git --exclude-dir=build --exclude="$SELF")
fail=0

echo "== [1/4] private paths / cluster SSH host / mail-user =="
if grep -RnIE "/home/mathiasr|tesis_maestria|UTE_FING|login\.cluster\.uy|--mail-user" . "${EXC[@]}"; then
    echo "  ^^ potential leak(s)"; fail=1
else echo "  clean"; fi

echo "== [2/4] credentials / keys (high-signal) =="
if grep -RnIE "(PASSWORD|SECRET|API[_-]?KEY|ACCESS[_-]?TOKEN)[[:space:]]*[:=][[:space:]]*[^[:space:]]+|-----BEGIN [A-Z ]*PRIVATE KEY-----|ssh-rsa AAAA|AKIA[0-9A-Z]{16}" . "${EXC[@]}"; then
    echo "  ^^ potential credential(s)"; fail=1
else echo "  clean (no inline credentials)"; fi
keyfiles=$(find . -path ./.git -prune -o -type f \
    \( -name '*.lic' -o -name '*.ilm' -o -name '*.pem' -o -name '*.key' -o -name 'id_rsa*' -o -name 'gurobi.lic' \) -print)
if [ -n "$keyfiles" ]; then
    echo "  ^^ committed license/key file(s):"; echo "$keyfiles"; fail=1
else echo "  no committed license/key files"; fi

echo "== [3/4] LSTM / Dantzig-Wolfe / column-generation under code/ =="
if grep -RnIE "LSTM|DantzigWolfe|GeneradorColumnas" code/ --exclude-dir=build; then
    echo "  ^^ residual private-development symbols"; fail=1
else echo "  clean"; fi

echo "== [4/4] emails (manual review only; not a hard fail) =="
grep -RnIoE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" . "${EXC[@]}" | sort -t: -k3 -u || true

echo
if [ "$fail" -ne 0 ]; then
    echo "SANITY: FAIL"
    exit 1
fi
echo "SANITY: OK"
