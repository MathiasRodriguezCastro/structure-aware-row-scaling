# Completed holdout and missing-control reassessment

The partial independent review identified a decisive missing control: extract the integer balance from the generator's pair of large opposing rows. The root investigator ran the resulting script, independently checked the saved data and completed this report after the reviewing agent became unavailable. This provenance matters: this is not a claim that the agent completed an independent final report.

## Exact results

The original holdout has 12 models (four seeds at three magnitudes), eight methods, two solvers and two presolve settings: 384 configurations, including 48 abstentions. The lattice control adds 48 actual calls. No assigned difficult case was removed. Native limits are 10 seconds and external limits 25 seconds. Four HiGHS calls hit the external limit; four other HiGHS calls returned their native time limit. Seeds are the independent generated profiles; magnitudes and presolve settings are repeated conditions.

| Method | Gurobi feasible / optimal | HiGHS feasible / optimal | Median rows | Median preparation (s) |
|---|---:|---:|---:|---:|
| Original | 12 / 7 | 15 / 15 | 25 | 0.000002 |
| GCD and RHS flooring | 15 / 10 | 15 / 15 | 25 | 0.000219 |
| Targeted integer clauses | 24 / 24 | 24 / 18 | 37 | 0.313005 |
| Full clause cover | 24 / 24 | 24 / 20 | 125.5 | 0.050279 |
| Lattice decomposition | 24 / 24 | 24 / 24 | 49 | 0.000449 |

Each solver/method has 24 configurations. Full results for all nine controls are in `guards-comparison-20260913/summary.csv`. Timings are descriptive and exclude separate exact post-run validation. Suboptimal targeted-clause outputs all use HiGHS presolve and are labeled `kOptimal`; they are feasible under both the exact original model and the claimed exported-row contract. A feasibility certificate cannot validate a global dual bound.

## Mathematical verification

- `verify_guard_experiment.py` independently enumerates the local original integer sets and recomputes all original optima by DP. It checks 144 block certificates and 145 selected clauses. Among bad local centers, 8,292 are covered by single original rows, 50 by joint original-row certificates, and 304 require a selected integer clause under the operational acceptance contract.
- `verify_intrinsic_witnesses.py` constructs 83 rational points in original bad cells and checks each against **every row of the global model**, including the resource constraint. All 12 models have such a witness. This proves row scaling and LP-valid additions cannot make the original relaxations intrinsically safe. The check uses exact original bounds, not the larger operational bound-tolerance box.
- The lattice decomposition has four small integer rows per block (the balance equality is two inequalities) and the original resource row. Its strict dominance certificates and all 64 local assignments establish integer equivalence. `analyze_guard_holdout.py` independently rechecks all 144 local equivalences, byte-identical original models, 48 rounded outcomes and a lattice-gap rounding certificate for every exported control row.

## Scientific consequence

The targeted compiler saves rows but is slower to prepare and does not protect all solver optimality results on this family. The direct lattice reformulation removes the apparent practical advantage. These data must not support a claim that the compiler improves on established preprocessing. More seeds from the same family would not fix the missing scientific distinction.

What remains useful is the explicit obstruction diagnosis: a rational feasible point near an infeasible binary center distinguishes an intrinsic limitation from a solver merely ignoring a declared tolerance. The theoretical route now includes exact thresholds and a one-row versus multirow complexity distinction. Its publication novelty and significance still require further review.
