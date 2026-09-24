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
3. **Solver-robustness campaign.** Pre-registered in `campaign-manifest.json`, described in
   Section 6 of the article and in the supplement: three solvers, four policies, two gaps, a
   hash-based split of 1,500 instances, family time limits from a registered rule, a replication
   subset with four further seeds, and an audit that reconciles every planned run.

## Confirmatory (registered before the data were seen)

- C1 Flat-GM/Base completed-run effort ratio.
- C2 PAR10 difference Flat-GM minus Base.
- C3 completion-rate difference Flat-GM minus Base.
- C4 sign stability of C1 and C2 across seeds.
- C5 stress experiment under CPLEX: budgeted versus budget-free paired discordance.
- Rules R1 (family time limits) and R2 (HiGHS scope), with their thresholds.

## Exploratory (post hoc, labelled as such wherever reported)

- Contradicted optimality claims and invalid dual bounds across runs of one instance. It is built
  on the registered verification endpoint but was added after a discordance appeared in the first
  records. Reported with a strict feasibility tier so that a barely infeasible point cannot
  manufacture a contradiction, and with a per-instance attribution for the one large case
  (`results-revision/solver-robustness/diagnostics/`).
- The diagnostic comparing the calibration subset with its pool (the subset is easier on Full).
- The HiGHS observation that a policy can decide whether any incumbent is found at all.
- Everything already listed as exploratory in the September 14 record.

## Not claimed

- No causal claim that scaling improves solver correctness in general: one instance is one
  instance, and the campaign reports the rate rather than a mechanism for all models.
- No cross-solver comparison of effort: work units, deterministic ticks and nodes are not
  commensurable and are only compared within a solver.
- No pooling of the two gap settings or of seeds as independent replications.
