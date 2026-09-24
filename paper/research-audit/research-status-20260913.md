# Scientific readiness reassessment — 13 September 2026

**Do not submit the previously packaged manuscript yet.** Technical reproducibility passed, but that was not enough to establish a sufficiently strong contribution. The user explicitly requested continued research until there are results worthy of submission. Work remains active.

## New falsification of the earlier experimental motivation

Classical integer-row GCD division and exact RHS flooring solve all 192 configurations per solver on the earlier binary stress experiment. The three added classical controls total 1,152 solver calls and all pass exact checks of the original rounded assignments and known optima. Data: `results-revision/research-audit/exploration-lattice/`. These are established presolve reductions, not a novel method. They must be included in any future manuscript using that stress set.

The independent failure diagnosis also separates original primal-budget violations, integrality amplification and solver failures; no failure in the earlier 3,456-configuration set was caused solely by the conservative 1e-9 acceptance threshold. Files: `results-revision/research-audit/exploration-failures/`.

## Current mathematical direction

The working note `paper/research-notes/joint-rounding.pdf` develops:

1. A joint Farkas/support-function exclusion test for an entire rounding cell.
2. A complete finite family of at most n+2 multiplier rays for a two-row binary block, generalized through a classical hyperplane arrangement to at most binomial(n+m,m-1) candidates for m rows.
3. An exact characterization of whether any row scaling can make near-integer acceptance safe: the original LP must avoid every infeasible integer center's rounding cell.
4. A coNP-completeness reduction for this intrinsic safety test, even for fixed small integrality tolerance, unit matrix coefficients, at most four entries per row, at most five entries per column, and a known integer feasible point. The construction is easily repaired by integer bound tightening; it is a hardness result about the given relaxation, not about finding a safe reformulation.
5. An exact weighted residual threshold and its strict boundary: the admissible scalar tolerance is smaller than the minimum bad-cell minimax residual. This yields a sharp common additional scaling factor when the threshold is positive.
6. A complexity contrast for one inequality: fixed positive integrality tolerance admits a polynomial interval-subset-sum algorithm with degree proportional to 1/eta; when eta is input, the decision problem is coNP-complete. The bound is impractical at usual solver tolerances and does not introduce a new general knapsack algorithm. Computing the exact one-row residual threshold still contains SUBSET SUM.
7. A compiler that distinguishes LP-redundant aggregate rows from necessary integer-valid strengthening, using established small-coefficient Boolean clauses for the latter. Its claimed practical advantage does not survive the new lattice control below.

The individual mathematical ingredients have substantial precedent. Coey–Lubin–Vielma already use certificate scaling to preserve guarantees under positive LP tolerances; Neumann–Stein–Sudermann-Merx study feasible rounding/granularity; MIPLIB 2010 describes tolerance-expanded feasible regions. Althoff–Stursberg–Buss supply classical zonotope normal enumeration; Bierlee et al. (CP 2026) study table encodings and cuts for ILP; TabID (JAIR 2025) automates subproblem tabulation. No claim of priority for Farkas certificates, no-good cuts, safe rounding, tolerance-based scaling, table compilation or zonotope geometry is made. See `joint-prior-art-20260913.md`.

The independent proof reviewer confirmed the initial remediability and hardness arguments and the fixed-m arrangement extension in partial messages, and found the zero-column wording defect (now fixed). The expanded weighted-threshold, sparse-copy and one-row results still need a completed independent written review; account limits interrupted the reviewers. Seventeen targeted mathematical tests pass, including exact signed-row enumeration, independent LP comparisons, sparse reduction instances, strict boundaries and integer input values beyond binary64 precision. Tests support the implementation but do not replace a proof review or novelty assessment.

## Exploratory evidence and limitations

`exploration-joint/` separates exact joint certificates from rowwise ones on a two-row cancellation family and tests 12-block selection problems. The joint certificate can succeed where every bound-aware single-row certificate fails. Solver outcomes still depend on the solver; classical row aggregation is an essential control.

`exploration-guards/` is an initial incomplete control design: the all-elimination arm incorrectly abstained on an uncertified block and baseline timing included unnecessary certificate generation. It must not be used as a fair performance comparison. `exploration-guards-v2/` corrects the all-elimination behavior and adds partial-assignment clauses. It still measures an unoptimized shared preparation path and is a pilot only. On its six generated models, targeted clauses return exact feasible rounded points, but HiGHS has two feasible, suboptimal outputs labeled optimal. Feasibility and global optimality therefore remain separate endpoints.

`guards-holdout-100/` was interrupted after a native solver call exceeded the intended time limit by several minutes. It has no complete run CSV and must not be analyzed as a completed campaign. The full assigned design is repeated under `guards-holdout-100-isolated/` with fresh child processes, a 25-second external limit, a 10-second native limit and one solver thread. Each completed configuration is flushed to JSONL. The algorithm, seeds 100–103 and all eight methods are retained; there is no removal of difficult cases. The new 72-variable instances have 12 six-variable blocks and an integer resource row. Optima are independently obtained by dynamic programming over exact local integer states.

The isolated campaign is **complete and independently verified**: 384 assigned configurations, 144 block certificates and 145 selected clauses checked. Targeted clauses recover feasible rounded points in all 24 configurations per solver, but yield only 18/24 exact optima with HiGHS (24/24 with Gurobi). All six suboptimal HiGHS outputs have presolve enabled and status `kOptimal`. Full clause covers give 24/24 feasible points and 20/24 exact optima with HiGHS. Four HiGHS calls in other arms hit the external limit and four hit the native limit; all remain in the comparison.

The independent rational witness constructor finds **83 exact global LP-feasible points in bad rounding cells, with at least one in every model**. All original rows and exact bounds are checked, including coupling after embedding the local witness. These points prove an intrinsic obstruction in every original model, without trusting solver behavior or the absence of a floating-point separation certificate.

The missing classical control has also finished: `guards-lattice-control-100/`. Writing each block as `(Mv+u; -Mv+w)`, integer dominance implies `v*z=0`; replacing it by that balance and `u*z<=floor(b1), w*z<=floor(b2)` preserves every integer assignment. The control has small integer coefficients and returns **24/24 exactly optimal rounded points with each solver**. Independent saved-data verification checks all 144 local equivalences, all 48 outputs and the lattice-gap certificate of every exported row. Median preparation is 0.000449 seconds versus 0.313005 for targeted clauses; median model size is 49 versus 37 rows. The targeted compiler has no demonstrated computational advantage on this family.

The full comparison is 432 assigned configurations, including 48 abstentions (384 actual solver calls). Four seeds are repeated at three magnitudes and two presolve settings; these are not 24 independent models. The primary endpoint is exact rounded feasibility, with exact optimality reported separately. No optimality guarantee is inferred from a primal certificate. Full results, a vector figure and interpretation are in `guards-comparison-20260913/` and `guard-holdout-review-20260913.md`. The active eight-page note includes these negative results.

## Remaining requirements

- Complete an independent written review of the expanded proofs, especially the one-row parameter distinction and the sparse-copy reduction; check precise novelty against the closest literature.
- Evaluate a narrower theoretical contribution centered on remediability, exact thresholds and complexity. The finite ray construction and interval-subset-sum algorithm should be presented as applications of established tools.
- Establish usefulness outside the two synthetic families, or make a convincing case for a sufficiently substantive theoretical note. Do not expand the current compiler benchmark merely to accumulate more favorable counts: its direct classical reformulation is already superior here.
- Once that scientific case survives review, rewrite the main submission manuscript around it. The earlier cover letter and submission ZIPs are frozen historical candidates, not the current research result. The active note and comparison are reproducible using the newly added Makefile targets.
