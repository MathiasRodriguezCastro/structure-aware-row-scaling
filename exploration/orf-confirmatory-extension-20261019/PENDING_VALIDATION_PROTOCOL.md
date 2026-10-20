# Base calibration and common confirmation references

This registered continuation follows the closed 256-assignment resource pilot.
It launches no confirmatory scaling comparison and changes no existing model,
policy, generator or manuscript. Pilot parents and confirmation parents remain
disjoint. Previous records, including infrastructure failures, remain intact.

## Operational resource calibration

Use only the seven Base cases in the three strata identified by
`BASE_RESOURCE_ASSESSMENT.json`. Repeat every feasible pilot case in each such
stratum at 120 seconds, seed 401, four threads, original tolerances and native
gap 0.001. Use fresh processes and the fixed Haswell/one-thread BLAS runtime.
If fewer than 80% reach the native gap stop, repeat the **entire** stratum at
300 seconds. Stop at the first passing cap, or at the 300-second resource ceiling.
At most 14 additional Base MIPs are attempted; no scaling policy is ranked.

The 80% rule is an operational target, not an independent optimality test. If
the 300-second ceiling does not meet it, report the missed target and retain
right censoring. Do not keep increasing caps, replace models or declare the
target passed. The resulting cap proposal is common to all four policies within
the solver/family/horizon stratum. Preserve 60 seconds for other pilot strata,
four solver threads, 8 GiB per allocation and one MIP process at a time. Final
resource settings and their limitations are frozen separately before confirmation.

## Common feasible reference procedure

Keep all 160 registered confirmation models. The exactly certified infeasible
Full/168 model is a diagnostic with quality not applicable; it requires zero
reference solves. For each other model, run original Base with Gurobi, seed 389,
120 seconds, native gap 0.001 and the original tolerances. Save every returned
candidate and use the final one to fix the original integer pattern.

Attempt the remaining LP with exact binary64-data rational coefficients,
SoPlex 8.1.0, 120 seconds and simplifier disabled. This setting follows the
documented pilot-reference recovery and is fixed before any confirmation
comparative result. Independently verify every original row, bound and integer
domain using exact fractions, and check the objective and witness hash. This
certifies a feasible reference and an upper bound, never MILP optimality.

If no verified witness is obtained, use one common Base CPLEX attempt with the
same seed, cap, gap and tolerances, followed by the same exact-LP procedure.
This fallback is triggered only by the failed feasibility acquisition, not by
relative policy performance or a preference for a lower reference objective.
Stop at the first independently verified witness. Do not reuse scaled candidates.
There are at most 318 reference MIP calls and 318 fixed-pattern LP calls; actual
counts, all failed attempts and their separate costs are retained. A preparation
failure before invoking SoPlex is not counted as an LP solve. Unknown models
remain unknown, are not replaced and are not scored as quality failures.

References are acquired in a fixed seed-shuffled order and frozen before any
comparative policy run. A separate replay verifies all admitted witnesses with
zero solver calls. Reference acquisition and calibration are serial, sharing
the same one-MIP concurrency limit. All heavy work uses compute nodes; file
transfers use ClusterUY port 10022 without login compression.

The 160 original Base exports are copied on a compute node from the already
verified all-model portability gate, checking both source and destination hashes.
Sources and protocol are hashed in `PENDING_VALIDATION_PLAN.json` before launch.
No staged job is allowed to mutate these dependencies. The continuation produces
resource/reference reports; it does not automatically release the 3,840 runs.
