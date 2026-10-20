# Bounded exact-feasibility recovery of common references

This continuation uses only failed common Base acquisitions, before any
confirmatory policy comparison. It preserves the original acquisition results,
reports, witnesses and raw seal. The original 160 models and all their bounds,
domains, rows and objectives remain unchanged.

Trigger: a registered reference is unknown after Gurobi and CPLEX, and a saved
fixed-pattern exact LP and its mapping are available. SoPlex's `unknown` status
does not establish infeasibility. The initial observed failures terminate without
a rational primal vector, with unsuccessful rational reconstruction/factorization.

Try at most the two saved patterns, Gurobi first, skipping identical recovery
subproblems (same fixed LP and cost ceiling). No new MIP calls, integer patterns
or solver seeds are permitted. For
each pattern retain every original fixed-LP constraint and bound verbatim.
Replace only the auxiliary LP objective with zero and add a cost-ceiling row.
The ceiling, in the original objective including fixed integer costs, is

    C_Base + 0.001 * max(1, abs(C_Base)),

where C_Base is the exact binary64-data objective of that saved common Base
candidate, rounding its integer coordinates as in the original fixed pattern.
This prevents accepting an arbitrarily poor witness from a zero-objective
feasibility phase. It does not claim C_Base is feasible or optimal. The ceiling
and coefficients are dyadic rationals written as exact ordinary decimals.

Use the same exact-LP settings, simplifier disabled, 120-second solver limit
and 180-second outer limit. Thus at most two extra LP calls per initially
unknown model, with zero extra MIPs. Stop at the first point that passes every
original row, explicit finite written bound, integer domain and cost ceiling
in independent exact arithmetic. Save every failed attempt and its cost.
Unknown cases remain unknown if the bounded procedure fails.

The feasibility subproblem is not the benchmark model: its extra cost ceiling
only restricts reference acquisition. Check the resulting point and its cost
against the original unmodified Base model. The old reference report is never
overwritten. Store successful recovery witnesses separately, produce a combined
reference-eligibility manifest before comparisons, and retain both provenance
chains in the final frozen reference mask.

Recovery starts after the initial acquisition, replay and raw seal. It uses
one compute allocation and a single exact-LP process at a time; no work runs
on login. The data population, budgets, scaling policies and comparative seeds
remain unchanged. This operational recovery provides no policy-ranking evidence.
