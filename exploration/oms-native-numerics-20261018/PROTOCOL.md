# Native numerical-risk study, registered locally before new solves

2026-10-18. Separate from OMS v1.3.14 and from the preceding well-behaved
multicommodity experiment. No artificial coefficient/unit perturbations.

## A. Selection and immutable screening

Inventory all instances in the full MIPLIB Numerics collection (not its Benchmark
subset). Eligible: at least one continuous and one integer variable, at most 60,000
variables, 100,000 source rows and 400,000 reported nonzeros, excluding known
infeasible/unbounded models. Previously investigated model groups are recorded
and excluded from the new-group stratum.

Stratum 1: choose the minimum-(nonzeros,name) representative per new group with
the decomposition tag; take its first eight representatives by the same order.
An unspecified group is an individual candidate, not a claim of independence.
Stratum 2: native industrial/energy examples gasprod1-2 (minimum nonzeros in
gasprod), cmflsp50-24-10-4 (the Numerics lot-sizing instance), and
minutedispatchstrategy (microgrid). Stratum 3: ta2-UUE is a new instance from the
already known network_design group, so it is not new-group confirmation.

Download native MPS and original DEC only, never a presolved DEC for an original
matrix. Check every row name. Infer private column ownership from the declared
local-row blocks; columns used in multiple blocks are shared, not reassigned.
A genuine master coupling row must touch private columns from at least two blocks.
Report row coupling separately from shared-column structure. Use the general
contract alone if the role structure is insufficient.

Numerical eligibility before solving: coefficient magnitude range >=1e6 or some
within-row range >=1e4, and at least one contract-modified L2 factor. Keep every
rejection, incompatibility, import discrepancy and lack of candidate.

Budgets are absolute algebraic precision goals 1e-1, 1e-3, 1e-5 and 1e-7, not
physical/operator standards. epsilon=1e-6 and integer rounding allowance
eta=1e-9. Select the tightest goal in that fixed grid for which every nonconstant
row has a compatible full integer-rounded contract. The raw-only interval is
diagnosed separately. A sufficient-contract incompatibility is not MIP infeasibility.
No feasible full-grid goal means abstention from the rounded-contract experiment.
Do not loosen a selected goal after observing solver outcomes.

Window [1e-9,1e9]; exact dyadic exports for all scaled arms. Flat-L2 and Budget-L2
share the nearest dyadic L2 target and coefficient window. Budget adds only the
residual lower bound. No private-column scaling; objective/bounds/domains unchanged.

## B. Establish an observed precision problem

Sequential fresh Gurobi 13.0.2 processes; Threads=4, seed=239, Presolve=-1,
ScaleFlag=-1, IntFeasTol=1e-9, MIPGap=.01, WorkLimit=1, TimeLimit=20 s.
Controls: Base, Base-tight, Dyadic-L2, Dyadic-L2-tight, Dyadic-L2-NumericFocus3.
FeasibilityTol=1e-6 normally, 1e-9 for tight controls. NumericFocus=3 only in its arm.
Run no Budget arm until the original-data verifier has identified the problem.
No returned point is an unknown accuracy outcome, not a precision failure.

Verify source binary64 data and saved binary64 points with rational arithmetic;
separate raw and integer-rounded residuals, bounds, exact integer domains, objective,
actually observed exported residuals, and the hypotheses of conditional transfer.
Rows with ranges are represented by their original lower/upper sides explicitly.
Never discard small coefficients silently. An import mismatch is an abstention.

## C. Evaluate only remedies for an observed problem

Run Budget-L2 only if some control with an incumbent fails the preselected goal
while its contract-compatible scaled export is different. Use the same seed and
limits. Keep successful strong controls in all comparisons, including Base.
If Budget does not improve verified delivery, close this candidate.

A promising remedy needs fixed-pattern exact feasibility/objective validation
before calling it an advantage: small residuals alone can mask an unrealizable
cost. A speed advantage needs the same verified quality objective and must include
selection/export/loading/solve costs; a low-work inaccurate point is not a win.

## D. Inclusion rule and stop

New paper material requires replication on at least two untouched instances or
three new seeds in a predeclared independent family, equal verified quality, and
either an accuracy recovery over strong controls or a >=20% complete-cycle
improvement without lost reliability. Preserve all exceptions and abstentions.
No manuscript edit for prettier matrices, active contracts alone, one favorable
seed, or a gain lost against Base/tight controls. Report unknown optimality as
unknown. If no candidate qualifies, close this bounded campaign without enlarging OMS.

## Parallel bounded mathematical note

Prove the commodity mean/contrast identity with correct zero-singular-value
bookkeeping. Investigate a common coupling factor for incidence blocks, including
rank-deficient B. Keep analytic spectral claims separate from computational speed
and native-data validation. No novelty claim without checking antecedents.
