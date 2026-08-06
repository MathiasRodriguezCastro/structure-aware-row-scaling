# Operational campaign — four final variants — verdict: Case 4

Small, decisive operational campaign for **Base / Flat-GM / Flat-L2 / Role-Hybrid**.
Purpose: does a role-blind Euclidean rule or a role-only kernel selection improve the
numerical *and computational* behaviour over Base and over the current variants?

## Design
- Families: Simple (15-instance deterministic subset), SG-Ter-Mer (15-instance subset,
  includes `instance014`, the hardest SGTM cell).
- Solver: **Gurobi** (ClusterUY, gcc13 container, 16 threads). CPLEX is not installed on
  the cluster; per the plan's Step 8 the CPLEX arm is run only if a signal appears — it did
  not, so it was not run.
- Gaps: 1% (0.01) and 0.1% (0.001). Fixed seed 42, timeout 1800 s, original-scale
  verification on. Same coverage/bands/clip/safeguards across variants.
- Metrics: solver wall time (PAR10) and Gurobi work units (deterministic); original-scale
  max relative residual; timeouts. Paired per instance; bootstrap CI on the geomean ratio;
  Wilcoxon. Full output in `analysis_time.txt`, `analysis_work.txt`; raw in each
  `gurobi_*/resumen.csv`.

## Result — no variant robustly beats Base
Per-cell geomean ratio vs Base (work units), with 95% bootstrap CI; a "win" requires the
CI upper bound < 1.

| cell | Flat-GM/Base | Flat-L2/Base | Role-Hybrid/Base |
|------|--------------|--------------|------------------|
| sgtm 1%   | 0.83 [0.42,1.71] | 1.20 [0.76,2.12] | 0.85 [0.42,1.80] |
| sgtm 0.1% | 0.77 [0.39,1.56] | 1.05 [0.65,1.85] | 0.81 [0.40,1.67] |
| simple 1%   | 0.63 [0.33,1.03] | 1.82 [1.04,3.47] | 0.63 [0.33,1.03] |
| simple 0.1% | 1.04 [0.86,1.24] | 1.44 [0.92,2.43] | 1.04 [0.86,1.24] |

Every CI straddles 1 except Flat-L2/Base on simple 1%, where Flat-L2 is **worse**.
Decision-rule tally (robustly-better / worse / neutral, 4 cells):
`Flat-GM 0/0/4`, `Flat-L2 0/1/3`, `Role-Hybrid 0/0/4`. **No variant robustly improves on Base.**

The SG-Ter-Mer cells show a suggestive *median* reduction (Flat-GM median work units
0.38-0.39, 11-12/15 wins), but it is not significant (p≈0.23-0.25, CI straddles 1), does not
transfer to Simple (neutral to slightly worse), and comes with a new timeout (below). Per
Step 8 the signal is neither clear, consistent across families, nor reliability-neutral, so
the campaign is not extended.

## Three sharp findings (verified against the raw rows)
1. **Role metadata is operationally vacuous.** Role-Hybrid ties Flat-GM in **15/15** Simple
   instances on *both* work units and nodes, and is within ~3-5% on SG-Ter-Mer. Selecting a
   coupling kernel by row role adds nothing over the role-blind Flat-GM. (Operational analog
   of the synthetic result that the coupling block metadata is inert.)
2. **The simple Euclidean rule is not safe.** Flat-L2 on `caso46e` reports status OPTIMAL
   yet its solution violates the original formulation by `max_viol_rel = 4.97` (≈497%). It is
   also robustly slower than Flat-GM (simple 1%, work units geomean 2.9x, Wilcoxon p=0.043).
3. **Scaling can hurt.** `instance077` (SG-Ter-Mer) times out under all three scaled
   variants but solves under Base within the limit — a reliability regression introduced by
   the scaling itself, independent of the kernel.

## Verdict: Case 4
No variant robustly beats Base; the "simpler" Flat-L2 rule is unsafe and slower; role-kernel
selection equals the role-blind kernel. The paper closes as a rigorous **attribution study**:
coverage explains part of the operational differences, the kernel (Euclidean vs geometric
mean) explains the synthetic advantage, block *and* role metadata do not deliver an
operational win, and comparing only against Base can produce incorrect attributions.
