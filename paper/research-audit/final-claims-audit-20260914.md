# Independent numerical and mathematical claim audit — 2026-09-14

The short manuscript's principal numerical counts are reproducible from saved data. Its positive interpretation can be made considerably clearer without restoring the invalid ownership attribution. One later control must remain visible: plain GCD division and RHS flooring verifies all 192 configurations per solver on the same stress set. Consequently, Budget-only's 191/192 result is a positive observation within the row-scaling comparison, not evidence of superiority to standard integer-aware preprocessing.

This audit edits no manuscript files and runs no solver. The fixed-basis reconstruction is assigned to a separate audit and is not certified here.

## Reproducible checks

Run from the repository root:

```bash
OPENBLAS_NUM_THREADS=1 python3 paper/research-audit/final-claims-verifier-20260914.py
```

The independent script imports no experiment runner, preprocessing implementation, or solver. It regenerates `final-claims-evidence-20260914.json` and `final-lattice-export-equivalence-20260914.csv` beside this note. It:

- enumerates all 4,096 binary assignments of each of the 96 frozen stress models using exact integer activities, and independently recovers every optimum;
- reclassifies every saved returned vector in all 3,456 budget configurations and all 1,152 later lattice-control configurations using the declared original-model acceptance rule;
- checks all 96 lattice-input hashes against the saved protocol;
- enumerates exact feasibility under the **actual binary64 exported coefficients and RHS** for all 288 lattice model/method combinations;
- checks all 240 operational records against their original summary records, recovers Work from all 240 native logs, and recomputes completed-pool Work and fixed-pool PAR10 ratios;
- checks the 1,080 fresh LP file hashes, independently counts exact byte identities, and recomputes the reported paired spectral summaries;
- reconstructs the older 30-seed headline medians and the 24-permutation ranks from their archived CSVs.

The matrix proportionality statement relies on the existing 1,080 row-audit records, whose all-pass status was rechecked; this new script does not independently reimplement the named LP parser or recompute all SVDs. The budget contract's exact factor/dyadic checks are supplied by the separate existing `scripts/research/verify_saved_experiment.py` and frozen `budget-final/verification.json`; this audit independently rechecks its optimum counts.

## 1. Budget experiment: complete verified counts

Every cell below has 192 planned configurations, representing 96 generated models with two presolve settings. Configurations are not independent statistical replications. “Verified” includes the declared requirement that the returned vector be within 1e-9 of its rounded binary vector, original bounds be respected within the stated threshold, and the rounded vector be exactly feasible with the enumerated optimum. Solver status alone is not the endpoint.

| Method | HiGHS verified | Gurobi verified | Abstentions per solver |
|---|---:|---:|---:|
| Base | 167 | 156 | 0 |
| GM | 141 | 140 | 0 |
| L2 | 141 | 139 | 0 |
| GM-tight | 166 | 166 | 0 |
| Dyadic-GM | 142 | 140 | 0 |
| Budget-only | **191** | **151** | 0 |
| Budget-GM | 182 | 152 | 0 |
| Budget-dyadic | 161 | 153 | 0 |
| Budget-round | 48 | 48 | 144 |

There are 3,456 planned configurations, 288 abstentions, and 3,168 optimizer calls. The current main text and Table S2 counts match. Budget-only should be visible in the main results, with its Gurobi count stated alongside its HiGHS count. The sentence about direct budget scaling outperforming minimax centering must explicitly say **on HiGHS**: on Gurobi the ordering is 151 versus 152, not the reverse.

Suggested wording:

> On HiGHS, direct Budget-only scaling verifies 191 of 192 configurations, compared with 167 for Base, 141 for GM and 182 for Budget-GM. Thus, in this stress pipeline, translating the residual budget directly into a row factor is more successful than adding coefficient centering. On Gurobi the corresponding counts are 151, 156, 140 and 152, so the improvement is solver-dependent.

This is not a claim that application-supplied engineering tolerances were validated: 0.01 is a declared stress-test budget. Nor does the experiment identify why HiGHS accepts different solutions, isolate internal presolve/scaling effects, or establish a runtime advantage. Those stronger claims require different experiments.

## 2. Later classical controls: essential context

The post hoc `exploration-lattice` campaign uses the exact same 96 saved input models. Each of the three methods, GCD-floor, GCD-floor-GM and GCD-midgap-GM, verifies all 192 configurations on each solver: 1,152 verified returned optima in total.

For the cleanest compact control, report **GCD-floor: 192/192 on each solver**, with 384 calls in total. This is ordinary exact integer coefficient GCD division followed by RHS flooring, not a proposed contribution. It preserves the binary feasible set but usually changes and strengthens the LP relaxation; it is not pure row scaling. Its exact actual export is integer-representable and was independently checked on all 4,096 assignments of all 96 models.

Suggested wording immediately after the budget comparison:

> A subsequent integer-aware control divides each integer row by its coefficient GCD and floors the RHS. It verifies all 192 configurations on each solver. This established reformulation exploits the discrete row activity lattice and changes the continuous relaxation; the budget experiment therefore supports an interpretable accuracy contract and a within-scaling effect, not an advantage over classical integer preprocessing.

This qualification need not erase the positive HiGHS result. Its purpose is to state which comparison that result supports.

### New arithmetic check on the optional GM variants

The old lattice protocol enumerated the integer-normalized constraints before floating-point GM multiplication. That correctly validates the ideal transformation but does not certify all independently rounded exported products. Exact enumeration of the stored binary64 exports gives:

| Method | Same actual binary set | Models excluding original feasible points | Models adding infeasible points |
|---|---:|---:|---:|
| GCD-floor | 96/96 | 0 | 0 |
| GCD-floor-GM | 36/96 | **60** | 0 |
| GCD-midgap-GM | 96/96 | 0 | 0 |

Across the 60 affected GCD-floor-GM model representations, 4,272 originally feasible assignment/model pairs are excluded by extremely small rounded boundary shifts. This counts repeated representations at the four exponents separately. Every recorded returned solution nevertheless satisfies the declared original-model optimum check. There is no inconsistency: solver tolerance can accept an original feasible boundary point that is infinitesimally outside the exact represented export.

Per-model counts are in `final-lattice-export-equivalence-20260914.csv` (288 rows). If all three methods are reported in the supplement, preserve this distinction. Do not describe every optional GM export as exactly integer-equivalent. Plain GCD-floor is unaffected and suffices for the substantive control. This finding also provides direct empirical support for the manuscript's existing warning that independently rounded arbitrary-factor products need not preserve a row exactly; it does not invalidate the dyadic proposition.

## 3. Operational results: conditional gain is real and must remain conditional

All 240 source summary records and all native Work log values were checked. The common pool is 14 SG-Ter-Mer instances at each gap and 15 Simple instances at each gap. The SG-Ter-Mer comparison is:

| Gap | Common completed n | Flat-GM/Base geometric mean Work ratio | Reduction on that pool | Fixed-pool mean PAR10 ratio |
|---|---:|---:|---:|---:|
| 1% | 14 | 0.6984131298 | 30.16% | 10.47343692 |
| 0.1% | 14 | 0.6824572104 | 31.75% | 9.071335946 |

At both gaps, instance077 has Base status OPTIMAL and TIME_LIMIT for Flat-GM, Flat-L2 and Role-Hybrid. Thus the requested statement is supported:

> Scaling produced a sizeable completed-run efficiency gain, but that gain was not robust to failure-sensitive aggregation.

“Approximately 30–32% less Work on the common completed pool” is accurate. “30–32% faster,” “a general solver speedup,” and “scaling improves operational reliability” are not established. Work is a solver-specific effort measure and differs from wall time. The two gaps reuse the instances and do not provide independent replications.

Simple Flat-GM/Base has Work ratios 0.63077262 and 1.06310847 at 1% and 0.1%, respectively. Its mean runtime/PAR10 ratios are 0.17786089 and 1.40345626. This supports the manuscript's stated lack of a uniform ordering; including every number in the main text is unnecessary.

## 4. Attribution: verified fresh and archived evidence

The fresh grid contains exactly 180 instances and 1,080 exports. Every stored LP hash matches. SA-Mat is byte-identical to Role-Hybrid on 136/180 and to SA-Mat-permB on 165/180. All 1,080 recorded whole-row proportionality audits pass. Their tolerance-based audit is not an exact rational transformation certificate.

| SA-Mat / control | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Role-Hybrid | 0.9390044058 | 1 | 1.079491708 |
| Permuted SA-Mat | 0.9996188669 | 1 | 1.000212309 |

The SA-Mat/Flat-GM medians are 0.9369705944, 0.1015248879 and 0.0097255704 at exponent ranges 1, 2 and 3. Independent relative-rank thresholding differs from the common reference rank in 25/1,080 exports. These facts support a large coupling-kernel explanation and smaller safeguard-dependent differences, not universal equality of production exports.

The archived 30-seed data also reproduce the headline medians: Base 530,294,097.06; Flat-GM (old `FlatMat`) 13,584.02; SA-Mat 1,333.79; Flat-L2 468.09. SA-Mat and the old `LocalGMCouplingL2` control agree on all 30 scalar diagnostics. SA-Pre is worse than that matched control on all 30, with median paired ratio 4.26834457. The 24-permutation sweep has true assignment best in 0/30 and median rank 18.

The **numbers** behind the old approximately 10.2-fold Flat-GM/SA-Mat comparison survive. The **block-ownership causal attribution** does not: local GM/coupling L2 reproduces the spectral result. The manuscript may keep the comparison as the confounded observation that motivates the matched control; it must never advertise 10.2-fold as identified metadata value. Condition numbers are numerical representation diagnostics and must not be used as automatic proxies for solver success, verified feasibility or effort.

## 5. Mathematical scope and wording

I found no error in the short manuscript's stated collapse, ownership-loss, triangular optimum, residual interval, re-emission or exact dyadic propositions. Their proofs support the positive mechanism and contract interpretation with the following scope preserved:

1. **Collapse:** every nonzero local row receives exact geometric-mean centering; extrema are not filtered. The skip-band extension allows only that safeguard. Coefficient-window vetoes and filtered extrema are separate implementation effects. The ownership theorem concerns candidate equality under those hypotheses, then equality under matched coupling safeguards.
2. **Spectral ratio bound:** it concerns the mathematical positive singular spectrum under an invertible diagonal row map. Empirical rank threshold changes are not covered by that exact statement; the fresh experiment correctly uses a common rank.
3. **Triangular optimum:** the closed form is exact for a common scalar factor in the locally whitened block triangular model. For one linking row it is whole-row Euclidean normalization including the aggregate coefficient. It is not a per-row optimum for arbitrary generated MIPs, an LP-basis theorem, or a runtime theorem. This constructive simplification deserves an explicit sentence in the abstract/introduction or mechanism discussion.
4. **Residual admissibility:** the interval is the complete set satisfying the stated scalar budget inequality and coefficient bounds. It is not the complete set of policies guaranteeing feasibility on a particular feasible region under all joint constraints. The exported-residual hypothesis is independent of the solver's parameter setting.
5. **Integer rounding:** the E term is a conservative independent-coordinate bound. Empty rounded-budget intervals certify incompatibility with that stated bound; they do not exclude smaller actual errors, cancellation or help from other rows. Later joint-row research strengthens this point but is outside the compact paper's current scope.
6. **Dyadic exactness:** the theorem correctly includes coefficient and RHS subnormal-grid/overflow constraints and representability of the factor itself. Arbitrary positive row re-emission invariance belongs to the continuous admissible construction; a dyadic factor restriction generally retains it only for power-of-two re-emissions. Decimal serialization must preserve the represented binary64 data.

Recommended positive formulation:

> After local whitening, the idealized coupling problem admits an explicit optimal common whole-row normalization requiring no ownership map. Residual budgets then supply an interpretable application input: they determine exactly when the requested coefficient and residual specifications can be met, and which centered factor satisfies them.

Avoid calling direct tolerance scaling, GM centering, power-of-two scaling, or GCD/RHS reductions new. The contribution is the tightly scoped characterization and attribution audit, with the combined contract and its implementation boundaries stated explicitly.

## 6. Compact evidence map and closure judgment

| Principal statement | Direct support | Interpretation boundary |
|---|---|---|
| Row scaling materially changes numerical representation | Reconstructed fixed-basis audit by the separate reviewer; fresh scaled spectral data also show the effect | Conditioning alone does not establish success or speedup |
| The large apparent ownership gain is a coupling-kernel effect | Exact collapse proposition; 136 fresh byte identities; matched spectral ratios; archived matched control | Specific statistic/construction, with safeguards outside exact hypotheses |
| Scaling can reduce solver effort in selected regimes | 0.698/0.682 completed-pool Work ratios, checked in 240 native logs | Completion-selected pool; PAR10 reverses after timeouts |
| Budget scaling can improve verified outcomes on HiGHS | 191/192 Budget-only versus 167/192 Base, independently rechecked | Declared synthetic budget; Gurobi 151/192; GCD-floor 192/192 on both |
| Budget specifications admit a complete explicit scalar test | Interval/minimax/invariance derivations | Conditional original-residual transfer, not solver feasibility guarantee |
| Rounding and export constraints can be audited | Rounding term; dyadic theorem; saved exact checker | Conservative row-wise contract; exact export alone not solver reliability |

No additional solver experiment is indispensable merely to support these **descriptive and conditional** statements. A stronger claim of a practically superior new preprocessing algorithm would require an application-level budget study and comparisons against established integer-aware reductions; the available evidence does not support it. Scientific publication readiness should therefore be assessed for the compact mechanism/contract contribution, not obtained by omitting the winning classical control or by claiming a universal new scaler.

All input/data/script SHA-256 values are in `final-claims-evidence-20260914.json`. The two principal saved-output hashes are:

- `budget-final/runs.csv`: `f0cfa86aa97e60dcca6985dd66b235883ecabafb1fe1f4de40a3b70b39840aa2`
- `exploration-lattice/runs.csv`: `80bbe151022da359801bf391e0c697acc5502018b9297a67cd590b9dc691e86f`

This audit supplies factual support and wording limits; it does not certify peer-review acceptance or establish unverified priority over the literature.
