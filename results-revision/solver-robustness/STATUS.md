# Solver-robustness campaign — status

Campaign id `solver-robustness-v1`. Design and pre-registration:
`paper/research-audit/solver-robustness-design-20260916.md` and `campaign-manifest.json`.

## Frozen artefacts

| Item | Where |
|---|---|
| Source commit | `699fddaf6c983966dc9f6cffd8bc9952f59e030e` (code freeze), `9d03e79` (run tables) |
| Cluster tree | `~/gars-robust/src-699fdda` (extracted through the transfer node) |
| Cluster binary | `code/build-robust/SistemaElectrico`, sha256 `d7279d978438547fa2203930a8f0839b0854d4f85a384fc4388dab18d07d7a19` (Gurobi 13.0.1 + CPLEX 22.1.2 + HiGHS 1.15.1, `-O2`) |
| Benchmark | `data/benchmark-v1/{simple,sgtm,completo}` (500 each) + `instance077-corrected` |
| Run outputs | `~/gars-robust/runs/<stage>/<solver>/<run_id>/{run.json,log.txt.gz}` |

## Progress

- [x] Inventory of the three pools, historical Base time-to-gap profiles, split and cost model.
- [x] Code: HiGHS backend, explicit tolerances, `--sin-kappa`, no-solution marker.
- [x] Stress experiment: CPLEX arm and CPLEX lattice controls (local, same 96 stored models).
- [x] Cluster build (job 5807818).
- [x] Smoke on the cluster: CPLEX (5807824) clean, 5 completed + 1 Full timeout at the 300 s
      smoke cap; HiGHS (5807825) exercises both censored outcomes. Gurobi deferred.
- [x] Pilot, CPLEX (5807908): 100/100. Simple completes 100% at 1800 s, SG-Ter-Mer 90%, Full
      86.7% at 1% and 80.0% at 0.1%.
- [ ] Pilot, HiGHS (5807909): Simple and SG-Ter-Mer done, Full running.
- [x] Caps by rule R1: Simple 1800 s, SG-Ter-Mer 1800 s, Full 3600 s (the Gurobi history misses
      the 0.1% threshold on Full at 1800 s). PAR10 penalty = 10x the family cap.
- [~] Rule R2: HiGHS keeps the full evaluation set on SG-Ter-Mer (90% Base completion) and only
      the replication subset on Simple (10%); Full pending its pilot.
- [x] Primary tables frozen for Gurobi and CPLEX (8,800 runs each).
- [~] Primary campaign: CPLEX submitted (5808803, 316 shards, throttle 24). Gurobi smoke 5808828.
- [ ] Multiseed, instance077 audit, HiGHS primary.
- [x] Analysis: job audit against the frozen tables, clustered multi-seed inference.
- [x] Paper: three-solver stress results and the campaign design subsection written.

## Licence coordination

The thesis 100k campaign (job 5807148) finished at 2026-09-24T10:13Z, so the Gurobi WLS licence
is free; only its postprocessing job remains and that one is pure Python. The Gurobi arm starts
with a low array throttle and the runner classifies any licence error as an infrastructure
failure, which is the only class of run that may be repeated.

## Known local findings before the cluster run

- HiGHS did not find any feasible solution for a Simple Base model within a 300 s cap (1,454
  nodes, 188k simplex iterations, dual bound 0.012% from the optimum), while Gurobi and CPLEX
  complete the same instance in seconds. Under Flat-GM it did find an incumbent in the same
  budget, so the policy changes which runs produce a solution at all. The pilot at 7200 s quantifies this;
  rule R2 then fixes the HiGHS scope.
- In the stress experiment, adding the residual budget to a centering rule never lost a verified
  configuration under CPLEX either, but it recovered none (0-0), against 41-0 on HiGHS and 12-0
  on Gurobi.
