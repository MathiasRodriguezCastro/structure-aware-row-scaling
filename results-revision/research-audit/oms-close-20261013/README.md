# Additional OMS dispatch validation (13 October 2026)

This experiment preserves the historical bank of 15 Simple and 15 SG-Ter-Mer inputs,
including known scenario defects. It does not pool new timings with the historical campaign.
The prospective protocol and input hashes are in `design.json`; `pilot/` is excluded.

- Comparison: Base, Flat-GM, pure row-only Ruiz-R4, Role-Hybrid, 120 paired calls.
- Ablation: six instances selected by list positions 1, 8, 15 per class; 12 additional calls
  for final-kernel Local-only and Coupling-only; reuse Base/full calls.
- Gurobi 13.0.2, four threads, seed 42, 120 seconds, 1% gap; calls are sequential.
- Residual contracts: demanding 0.01 MW/100 m³, reference 0.1 MW/1,000 m³,
  permissive 1 MW/10,000 m³. These are study objectives, not UTE tolerances.
- Coverage: 129,600 physical rows per comparison policy. Three scenarios with four policies
  give 1,555,200 decisions; partial-stage audits add 155,520 decisions.
- Whole-row/RHS equivalence, unchanged objective/bounds/integer domains, named Base bases,
  conditioning before/after ten documented equilibration passes, original-unit incumbents.

`exports/` contains gzip-compressed LPs and named row factors/bases. `runs/` contains native
Gurobi logs and binary64 incumbent vectors. `runs.csv` retains work, total time and PAR10
for every recorded call. `factor-contracts.csv.gz` retains each proposal → inward-rounded
interval → applied factor. `physical-verification.csv` records exact rational physical
residuals and pointwise export defects separately from the assumed exported-row limit.
Whole-model row/bound/integrality diagnostics are floating-point. Primal verification does
not independently certify dispatch optimality.

`protocol-amendments.json` records an LP positive-sign serializer repair made before the
first new optimization call; it leaves coefficients, factors and conditioning unchanged.
Four observations with empty incumbent archives after interruption were repeated and
replaced; `artifact-recovery.json` preserves the criterion and confirms unchanged work,
objective, nodes, gap and row diagnostics. Superseded CSVs are provenance, not extra
observations. Atomic incumbent saving was added. Execution can resume from recorded calls using the same frozen protocol; preserved partial
logs from an interrupted attempt do not add an observation to the paired sample.

From the repository root:

```sh
# Read-only verification of preserved results, no solver license required:
make research-oms-check
# Regenerate compact tables from stored summaries:
python3 scripts/research/oms_dispatch_tables.py
# Fresh campaign: choose a new directory; prepare requires a solver-free C++ executable
# and the archived Base reference bases, run requires a full Gurobi license.
python3 scripts/research/oms_dispatch_validation.py prepare --out /path/to/new-output
python3 scripts/research/oms_dispatch_validation.py run --out /path/to/new-output
python3 scripts/research/oms_dispatch_validation.py summarize --out /path/to/new-output
```

If a budget changes factors, those changed exports need a separate matched evaluation.
Here all factors remain admissible in all scenarios, so the budgeted exports coincide with
those already optimized. No duplicate MILP calls are used to claim a budget performance gain.
