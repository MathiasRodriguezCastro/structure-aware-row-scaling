# Matched accuracy controls — OMS research note

Six known SG-Ter-Mer models × two presolve settings × three seeds × four policies.
The frozen design has 144 terminal comparisons. One host reboot caused an additional
interrupted native attempt; its partial output and the pre-reboot record are retained
under `interrupted-attempt/`. See `RESTART_AMENDMENT.md`. No models, parameters or
endpoints changed. This is within-family confirmation, not external validation.

Read `RESULTADOS.md` and `matched-accuracy-note.pdf` for the complete results.
`verified-runs.csv` retains every terminal outcome and disjoint timing stages;
`verified-cases.csv` retains per-model results, `verified-pairs.csv` the matched
cost comparisons, and `paired-summary.json` their explicit denominators.

From the repository or the root of a clean archive extraction:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 exploration/oms-matched-accuracy-20261016/independent_check.py
python3 exploration/oms-matched-accuracy-20261016/write_report.py
python3 -m unittest discover -s exploration/oms-matched-accuracy-20261016 -p test_endpoints.py
```

Replay requires Python, NumPy, SciPy and highspy as an LP reader, without native
optimizer calls or commercial solver imports. All twelve exact feasible witnesses
are supplied and checked against every row, bound and integer domain of the actual
matching native export. Witness feasibility does not prove global optimality.
`VALIDATION.json` reports the checks; `PACKAGE_VALIDATION.json` describes replay
from a clean extraction with optimizer execution blocked.

`study.py` is the frozen native runner and `snapshot-study.py` its byte-identical
copy. It records the original C++ executable hash, solver version, parameters,
input/model hashes and fixed randomized order. The binary and a Gurobi license
are not required or supplied for saved-point replay. Native generation/solving
belongs in a new experiment directory, using the full generator repository and
an explicitly new design; the frozen study refuses to overwrite its design/results.

Timing covers complete fresh processes and spans a host reboot. These are local
prototype measurements under changing shared-machine load, not a hardware benchmark.
Work is the primary native effort measure. Terminal budget compliance is distinct
from objective quality, reported gap and independently detected bound discrepancies.
No timing is claimed to measure first delivery of a verified incumbent, and no full
precision–cost frontier is inferred from a single declared budget.

The prior OMS v1.3.8 snapshot and all previously closed research ZIPs remain intact.
Code is MIT; data/results are CC BY 4.0, as stated in the supplied licenses.
