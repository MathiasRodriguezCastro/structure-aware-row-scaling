# Prospective within-family validation of the frozen Budget-L2 policy

Date: 18 October 2026. This protocol precedes every new optimization call.

The policy is exactly `choose(..., 100)` from the archived multi-budget study:
0.01 MW and 100 m3, coefficient window [1e-9,1e9], exported residual hypothesis
1e-6, integer allowance 1e-9 and the existing activation export reserve.
No parameters, budgets or instances will be selected from the new outcomes.

## New scenarios, and the limit of their independence

Generate 24 scenarios: eight each at 24, 72 and 168 hourly periods. Round-robin
parents are the six demand-inversion-free historical inputs. A fixed PRNG
(2026101811) selects a contiguous window and independently perturbs inflow by
0.90–1.10 and both demand series by the same hourly factor in 0.90–1.10.
Other plant parameters, units and the original generator remain unchanged.
This produces new parameter scenarios and matrix dimensions, not a new
application or a held-out sample of observed operational data. Parent inputs
were known during policy development. The new perturbations and windows were
not; all 24 are retained regardless of outcomes. Check local <= total demand,
original integrality, unique model hashes and variable/constraint counts before
the first solve. Never call these scenarios external validation.

## Fixed comparison

Policies: Base, Base-tight, L2, L2-NF3, Budget-L2. Three seeds 101,137,173:
360 MIP calls, interleaved by PRNG 2026101812, sequential fresh local processes.
Common Gurobi 13.0.2 parameters: Threads=4, TimeLimit=120 s, MIPGap=.01,
Presolve=-1, FeasibilityTol=1e-6, IntFeasTol=1e-9, ScaleFlag=-1,
IntegralityFocus=0, NumericFocus=0. Base-tight changes only FeasibilityTol to
1e-9. L2-NF3 changes only NumericFocus to 3. The L2 controls use exactly the same
kernel and coefficient window as Budget-L2, with its physical contract disabled.
No starts. No retries or disappearance of failed attempts. Preserve every log,
point, status, timing and hash. Full-process timing includes generation, policy
preparation, native import, optimization, verification and persistence, on a
shared local host. No parallel MIP jobs or cluster login work.

## Endpoints and accounting

Report all model/seed pairs: exact rational original-unit row residuals before
and after rounding integer variables, bounds, integrality, original objective,
native status, work, nodes, full-process seconds. Distinguish observed exported
residual from the assumed 1e-6 contract bound. Record all changed factors and
their ratios to conventional L2. An abstention is an outcome, not a dropped case.
Paired work/time geometric means include positive observations; missing points,
timeouts, failures and contradictions are reported separately and never called
speedups. Report each size stratum as well as the complete sample. Summarize
candidate objective deterioration relative to each control, without treating
incumbents as MILP optima. Do not select a favorable subset after seeing results.

For each model, attempt one global rational LP certificate (all binary variables
relaxed, 30 s) and one integer-pattern repair per distinct representation (Base,
L2, Budget-L2; 30 s). Choose each repair's point by lowest original candidate
objective across that representation's policies/seeds, with lexical tie break.
Check every rational point against every original row, bound and integer domain;
verify dual signs, stationarity and objective independently. Check feasible
witnesses of the actual solved representation against reported bounds, with
the historical 8-ulp/1e-6 screen and 1% completion criterion. Unknown certificates
stay unknown. Missing bound contradictions do not establish optimality.
Report work/time both without and with detected-contradiction exclusions, and
the number excluded. Certificate acquisition is a separate, reported cost.

## Decision and scope

The study tests prospective within-family transfer and the incremental effect of
the contract over L2. It does not establish superiority or explain solver internals
causally. Adverse and null results belong in its report. An independent second
application and a general performance predictor remain separate claims. No
additional budget search, solver sweep or new scaling algorithm is authorized
by this protocol. Keep the submission's old frozen evidence intact.
