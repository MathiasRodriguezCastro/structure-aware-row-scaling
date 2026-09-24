# Operational findings after reconstruction

Audit date: 2026-09-09. Reproduce the tables and figure with
`python3 scripts/audit_operational_evidence.py` from the repository root. Historical
`resumen.csv` and logs were not edited. The raw campaign has 240 assigned runs,
234 solver-completed runs and six time-limited runs; the wrapper labels all 240
as `OK`, which is not a solve-completion criterion.

## Main table

Mean PAR10 in seconds, with completed runs out of 15 in parentheses. A
non-completion receives 18,000 seconds for the 1,800-second time limit.

| Class | Gap | Base | Flat-GM | Flat-L2 | Role-Hybrid |
|---|---:|---:|---:|---:|---:|
| Simple | 1% | 11.90 (15) | 2.12 (15) | 20.44 (15) | 2.11 (15) |
| Simple | 0.1% | 52.00 (15) | 72.98 (15) | 33.17 (15) | 72.63 (15) |
| SG-Ter-Mer | 1% | 116.15 (15) | 1216.51 (14) | 1217.60 (14) | 1217.34 (14) |
| SG-Ter-Mer | 0.1% | 134.08 (15) | 1216.24 (14) | 1216.05 (14) | 1216.91 (14) |

The table is available as `main_table_four_cells.csv` and
`main_table_four_cells.tex`. It is a descriptive result from one seed and a
deterministic, previously selected 15-instance subset in each class. No variant
has a consistent advantage across the four cells. The bad SG-Ter-Mer PAR10
outcomes arise from one instance, `instance077`, timing out for every scaled
method at both gaps while Base completes. This is six observations on one
instance, not six independent failures.

## Work instrumentation and reconstruction

The preprocessing report leaves `std::cout` in `fixed` with precision zero.
The historical `[NUM-EFIC]` marker inherits that format. Every scaled Work value
in the CSV is therefore an integer, while Base retains decimals: 178 of 180
scaled markers disagree with the native Gurobi two-decimal Work summary by more
than half a native reporting unit. Twenty-eight scaled markers round to zero.
For example, `instance001` / Flat-GM / SG-Ter-Mer 0.1% has 7.28 native Work units
and marker `work=7`.

The former script additionally assigns 18,000 to timeouts when the requested
metric is Work. That mixes seconds and Work. Its geometric mean drops zero
numerators, while its reported paired count and win tally retain them. Its
printed decision criterion mentions residual validity and new timeouts, but the
implemented tally tests only the bootstrap interval. These defects invalidate
the old Work summaries as quantitative evidence.

`reconstructed_runs.csv` recovers Work from all 240 native logs to a common
0.01-unit resolution. `paired_contrasts.csv` reports Work only for the same
all-methods-completed subset in a cell: 15 Simple instances and 14 SG-Ter-Mer
instances. It never substitutes seconds for Work. Each contrast includes
rounding-only bounds and an exploratory paired bootstrap interval.

On the 14 completed SG-Ter-Mer instances, Flat-GM/Base has Work geometric ratios
0.698 [0.486, 0.944] at 1% and 0.682 [0.470, 0.925] at 0.1%. These are favorable
conditional comparisons; they coexist with the much worse full-pool PAR10 and
do not establish superiority. The two gap settings share the same instances.

Role-Hybrid and Flat-GM have identical node counts and Work rounded to 0.01 on
all 15 Simple instances at both gaps. In SG-Ter-Mer only five node counts match
and none of the native Work values are identical. Equality of rounded Work is
not proof of identical solver trajectories or coefficient matrices.

## Residual interpretation

The Flat-L2 / `caso46e` / 1% solution has an absolute equality residual 4.9704
on `a1_g2h_def(7)`, with RHS zero. The historical metric
`max_viol_rel = max_r violation_r/(1+abs(rhs_r))` is consequently 4.9704 too.
Calling this a 497% error is incorrect: its denominator here is the arbitrary
unit floor, not a physical reference quantity. The maximum
activity-normalized residual of the same solution is 1.15054e-7. Both should be
reported. The evidence supports sensitivity to representation and tolerance;
it does not by itself establish physical unacceptability.

`cell_summary.csv` retains all 15 assigned rows per variant when reporting
residual maxima and sensitivity counts. It separately gives failures of an
absolute 1e-6 test and activity-normalized 1e-8 and 1e-6 tests, together with
original bound/integrality checks. These are explicitly declared sensitivity
thresholds, not selected deployment criteria. Availability requires no missing
solution values. All 240 rows have available verification.

## Precision fix validation

The Gurobi source now emits `[NUM-KAPPA]` and `[NUM-EFIC]` through fresh
`ostringstream` objects with `max_digits10`, independent of global `cout`
formatting. No solver parameter or mathematical operation changed.

The changed translation unit compiled. The existing local build includes both
Gurobi and CPLEX, so the binary was linked with that same backend combination.
A local one-thread two-run smoke test on `caso01a`, Base and Flat-GM, completed
optimally and verified that parsed Work preserves the marker exactly and lies
within 0.005 of the native log summary. The resulting markers were
1.682544726739841 and 1.792427224321357. Evidence is in
`precision-smoke/validation.json`; these smoke timings are not campaign data.

## Limits

The bootstrap intervals resample instances within a cell and are exploratory.
There is no cross-cell pooling or multiplicity-adjusted superiority claim.
Small samples, one influential timeout, repeated gap settings, prior instance
selection, and one solver seed limit generalization. Work is conditional on
completion and remains rounded; original-scale feasibility does not certify
global optimality. Use the direct algebraic and matrix controls to establish
metadata attribution, and this campaign to show why operational and numerical
endpoints must remain separate.
