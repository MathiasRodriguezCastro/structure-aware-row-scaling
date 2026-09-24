# v1_simple_000293: a second contradicted optimality claim, and a build that does not share it

Same signature as `v1_simple_000344`, with one difference that matters for how it is reported.

## What happens

Gurobi 13.0.1 through the C++ interface, one thread, seed 1, gap 1%, on the cluster and
reproduced locally on a different CPU:

| Policy | Objective | Dual bound | Gap | Nodes |
|---|---:|---:|---:|---:|
| Base | -1.317221e8 | -1.317221e8 | 0.0000% | 1 |
| Flat-GM | -2.908777e8 | -2.923059e8 | 0.4910% | 1 |
| Flat-L2 | -2.912783e8 | -2.922794e8 | 0.3437% | 832 |
| Role-Hybrid | -2.908777e8 | -2.923059e8 | 0.4910% | 1 |

The scaled points verify against the original model (activity-normalised violation 1e-13), so
the Base run reports as optimal a point that captures 45% of the achievable objective, with a
dual bound above the optimum. Its own log shows a root relaxation of -2.923059e8, which no run
of the tree could legitimately turn into a final bound of -1.3172e8.

## The difference from instance 000344

Solving the exported model directly with gurobipy 13.0.2 (`direct-gurobi.json`) gives
-2.907548e8 at default settings and between -2.905e8 and -2.909e8 under NumericFocus 3,
presolve off and ScaleFlag 2: **this build does not reproduce the failure**. For 000344 the
default direct solve reproduced it exactly. We do not attribute the difference between builds;
we report that one of the two cases survives a later patch release and the other does not, and
that the campaign ran 13.0.1 throughout.

## Why the run alone cannot show it

Nothing inside the Base run is self-contradictory: the incumbent is above its own dual bound,
the residuals are at round-off, the model statistics only draw the usual warnings about large
coefficients (matrix range [3e-03, 2e+09], RHS range [5e+00, 7e+09]). It takes a second
representation of the same model, solved and verified, to expose the error.
