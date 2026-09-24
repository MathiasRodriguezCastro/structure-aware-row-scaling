# Revision record, 2026-09-24

What this round changes, and which claims are confirmatory and which exploratory. It extends
`editorial-revision-20260914.md`; nothing there is withdrawn.

## Changes

1. **Stress experiment reported on three solvers.** The CPLEX arm (1,728 calls on the same 96
   stored models, plus 576 GCD controls) was already run; the text described two solvers. The
   article, the tables and the figure now report all three, and the claims verifier re-derives
   every CPLEX verification flag by exact enumeration.
2. **SG-Ter-Mer scenario defect declared.** 39 of 68 historical instances, 9 of the 15 used in
   the operational campaign, carry a total-demand series that falls below local demand in some
   hours. The models stay valid MILPs and no reported comparison is affected; the new campaign
   uses the corrected pool. Check: `scripts/research/check_sgtm_demand.py`.
3. **Solver-robustness campaign: prepared, partly run, then descoped.** It was pre-registered
   in `campaign-manifest.json`, its time limits were fixed by rule R1 from the calibration
   pilot, and 9,057 runs were executed before it was stopped. It is **not** part of this
   manuscript: the paper argues that solver effort and acceptance are pipeline-dependent, and a
   benchmark of tens of thousands of runs would not change that thesis. The protocol, the frozen
   tables and the runs stay in `results-revision/solver-robustness/` for a separate study, and
   the article and supplement no longer mention them.

4. **The residual contract stated on the application.** Interpretable tolerances are declared
   for the rows of a real instance and Proposition 5.1 is applied to its 4,320 rows
   (`results-revision/research-audit/application-budgets/`). It needs no solver and adds no
   experiment: the budgets are declared by the modeller, which the limitations say plainly.

5. **Narrative and precision pass.** The title now says *generated* mixed-integer programs; the
   introduction states the paper's single question and says which contribution answers which
   half; Section 4 ends on the bridge to Section 5 and Section 5 opens by picking it up. Claims
   a referee would question were tightened: the illustrative budgets are the modeller's, the
   collapse result and the triangular optimum are stated separately, the abstract says the basis
   is fixed per model and names the subset behind the 30--32 percent, the comparator is explicit
   wherever a budgeted rule "never lost" a configuration, the admissibility claim is backed by
   checking all three kernels on every row, Proposition 4.2 is written with the pseudo-condition
   number, and the stress counts are introduced as what they are rather than as failure rates.

6. **Sensitivity to the scenario defect** (supplement): both endpoints repeated on the six
   SG-Ter-Mer instances without the demand inversion.

## Confirmatory (registered before the data were seen)

- C5 stress experiment under CPLEX: budgeted versus budget-free paired discordance. This is the
  only registered contrast of the campaign that the manuscript reports, because the CPLEX arm
  of the stress experiment is part of the paper.
- C1 to C4 and the rules R1 and R2 concerned the descoped campaign and are not reported.

## Exploratory (post hoc, and not reported in the manuscript)

Everything below comes from the descoped campaign and is kept in the repository only:

- Contradicted optimality claims and invalid dual bounds across runs of one instance, with a
  strict feasibility tier and a per-instance attribution for the two large cases
  (`results-revision/solver-robustness/diagnostics/`).
- The diagnostic comparing the calibration subset with its pool (the subset is easier on Full).
- The HiGHS self-check that rejects its own optimality claims.

Everything already listed as exploratory in the September 14 record still applies to the
manuscript.

## Illustrative, not measured

The dispatch budgets of Table 5 are stated by us to show what the contract implies. No operator
tolerance was supplied or validated, and the paper says so where the table is introduced and
again in the limitations.

## Not claimed

- No claim, in the manuscript, about how often a solver returns a point contradicted by a
  verified solution: that evidence exists in the repository but the paper does not use it.
- No cross-solver comparison of effort: work units, deterministic ticks and nodes are not
  commensurable.
- No universal solver speedup or reliability improvement.
