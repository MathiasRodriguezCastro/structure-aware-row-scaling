# v1_simple_000344: an optimality claim contradicted by a verified solution

Found while checking the first records of the primary campaign. It is a diagnostic, not a
registered endpoint: the registered verification endpoint checks each returned point against
the original model, and comparing those verified objectives across runs of one instance is a
check added afterwards.

## What happens

Gurobi 13.0.1, one thread, seed 1, MIP gap 1%, feasibility tolerance 1e-6, integrality 1e-5.

| Policy | Objective | Dual bound | Gap | Nodes |
|---|---:|---:|---:|---:|
| Base | -2.420574e8 | -2.420574e8 | 0.0000% | 1 |
| Flat-GM | -4.546138e8 | -4.556300e8 | 0.2235% | 1 |
| Flat-L2 | -4.550899e8 | -4.556046e8 | 0.1131% | 498 |
| Role-Hybrid | -4.546138e8 | -4.556300e8 | 0.2235% | 1 |

The three scaled points are accepted by the verifier against the **original, unscaled** model
(activity-normalised violation 1e-13, integrality 0, no missing variables), so the optimum is
at most -4.5461e8. The Base run therefore returns a point 46.8% worse while reporting a zero
gap, and its final dual bound (-2.4206e8) is above both that point and its own root relaxation
(-4.5563e8), which no valid bound for a minimization can be.

## Attribution

`scripts/research/diagnose_contradiction.py` exports the unscaled model and solves that file
directly with gurobipy 13.0.2, outside the C++ pipeline (`direct-gurobi-raw.json`):

| Setting | Objective | Nodes |
|---|---:|---:|
| default | -2.420574e8 | 1 |
| NumericFocus 3 | -4.544957e8 | 1 |
| Presolve off | -4.544957e8 | 48 |
| NumericFocus 3 + presolve off | -4.544957e8 | 358 |
| ScaleFlag 2 | -2.420574e8 | 1 |

The wrong answer reproduces from the exported file with a different gurobipy build, so it is
not an artefact of our pipeline. Turning presolve off or raising the numerical emphasis
recovers the right answer; the solver's own scaling option does not. The unscaled model carries
a matrix range of [3e-03, 2e+09] and an RHS range of [5e+00, 7e+09], and Gurobi warns about
large coefficients, large right-hand sides and large bounds; under Flat-GM the matrix range is
[2e-05, 4e+04] and only the bounds warning remains.

## Files

- `repro-gurobi-344-*.json`: local reruns of the four policies, bit-identical to the cluster.
- `base-gurobi-log-excerpt.txt`, `flatgm-gurobi-log-excerpt.txt`: coefficient statistics,
  presolve, root relaxation and final line of each run.
- `direct-gurobi-raw.json`: the five direct solves.
