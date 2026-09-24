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
- [ ] Smoke on the cluster: CPLEX (5807824) and HiGHS (5807825) submitted; Gurobi deferred.
- [ ] Pilot (Base only, CPLEX and HiGHS, calibration set, cap 7200 s).
- [ ] Cap decision by rules R1/R2 (`scripts/research/robustness_calibration.py`).
- [ ] Primary campaign, multiseed, instance077 audit.

## Licence coordination (blocking for the Gurobi arm)

The cluster is running the thesis 100k campaign (jobs 5807148-5807150), which uses the Gurobi
WLS licence. Running our Gurobi arm at the same time risks exhausting the concurrent sessions
and breaking *that* campaign, so every Gurobi stage waits until it finishes. CPLEX and HiGHS
do not touch that licence and run meanwhile.

## Known local findings before the cluster run

- HiGHS did not find any feasible solution for a Simple Base model within a 300 s cap, while
  Gurobi and CPLEX complete the same instance in seconds. The pilot at 7200 s quantifies this;
  rule R2 then fixes the HiGHS scope.
- In the stress experiment, adding the residual budget to a centering rule never lost a verified
  configuration under CPLEX either, but it recovered none (0-0), against 41-0 on HiGHS and 12-0
  on Gurobi.
