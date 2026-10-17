# Matched accuracy and numerical-remedy comparison

Fixed on 16 October 2026 before any new MILP call. OMS v1.3.8 and all previous
research archives remain intact. All work is local; no ClusterUY login execution
or transfer is used. The machine is shared with another thesis computation, so
wall times describe this prototype; native Work is the primary effort measure.

## Questions and stopping rule

1. Does the presolve-off Budget-L2/L2 precision contrast extend beyond instance046
   to the six archived SG-Ter-Mer models without the documented demand inversion?
2. At the same declared precision, how does Budget-L2 compare with ordinary L2,
   global tolerance tightening, and NumericFocus=3 under identical settings?

Exactly one factorial campaign: six known models (001,005,022,027,031,046), seeds
11,23,47, automatic/off presolve, four policies = 144 new MILP assignments.
These are known models and previously used seeds, not independent application
generalization or predictive validation. Every assignment is retained. No new
reference LPs, tuning after outcomes, demand repairs, new kernels or second-family
campaign are part of this study. Stop after this cohort and its independent replay,
whether results are favorable, mixed or negative.

## Mathematical intervention and controls

Only complete rows and RHS are scaled. Objective, variable bounds and original
integer domains remain unchanged. The conventional and budgeted exports must
reproduce the frozen native files exactly by SHA-256 before each solve. Every
treatment rebuilds the original C++ model exactly once from the original input.

- L2: coefficient-only L2 with coefficient-window projection [1e-9,1e9], no
  identity-band veto, primal tolerance 1e-6 and integer tolerance 2^-28.
- Budget-L2: identical L2 kernel and integer tolerance; demanding study targets
  0.01 MW and 100 m³ with the original per-row conversions, integer and finite-box
  export reserves. Exactly 1,440 activation factors change per model.
- L2-tight: the identical L2 file, primal and integer tolerances 1e-9.
- L2-NF3: the identical L2 file and matched tolerances, NumericFocus=3.

Gurobi 13.0.2, four threads, TimeLimit=120 s, MIPGap=0.01, ScaleFlag=-1,
IntegralityFocus=0, Presolve in {-1,0}; no MIP starts. Other parameters use defaults.
Each instance/presolve/seed has all four policies. A fixed random permutation
(seed 20261016) determines the 144-call sequential schedule before optimization.

Positive scaling preserves the exact-arithmetic model. Arbitrary-factor product
rounding can change the imported binary64 model; all bound comparisons therefore
use exact feasible witnesses of the actual matching native export, not an assumed
equivalence. The already supplied twelve L2/Budget-L2 witnesses are rechecked.
L2-tight and L2-NF3 use the same export and witness as L2.

## Endpoints and cost accounting

Primary endpoint: the terminal returned point satisfies the audited original-unit
budgets after integer rounding. Missing candidates count as failures of delivery.
Record raw and rounded residuals and their budget ratios, changed factors, integer
and bound diagnostics, objective, native status/gap, Work and nodes. These budgets
are numerical study goals, not operator standards. Passing them is not a proof of
global MIP feasibility or optimality.

Separately flag reported lower bounds above an independently checked exact feasible
objective U of the same file, allowing max(1e-6,8 ulps(B)) for presentation; flag a
native 1% completion when U<C-0.01|C|. Absence of a flag does not certify a bound.
Terminal budget compliance and detected bound discrepancies are separate endpoints.

Each fresh Python process is timed end to end: imports, generator construction and
Base writing, metadata, factor selection, export, native import and equality checks,
solve, extraction, verification and persistence. Disjoint internal stages are retained.
Compilation and previous witness acquisition are offline costs. No common preparation
is omitted or amortized; current witness revalidation is timed separately.

This measures terminal delivery at the solver's native stopping rule, not time to
first verified incumbent or a tuned precision-cost curve over multiple budgets.
Report cost and objective together. Faster native termination, a smaller residual,
or no known bound contradiction alone does not establish superior optimization.
Do not pool Work across different presolve configurations or silently exclude
timeouts. Joint-pass paired ratios are descriptive and conditional; if there are
none, report them as unavailable.

## Incorporation criterion

Only add a compact result if it materially clarifies the existing accuracy/software
contribution. If precision recovery occurs only in instance046, retain case-study
language. If other remedies match or improve the result, report that fact. A benefit
only with presolve disabled is not evidence of an advantage under default presolve.
Generalization to another generator and a full precision-cost frontier remain
separate questions; they are not inferred from this experiment.
