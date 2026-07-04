# Cluster job templates (reproduction level N2)

Generic SLURM templates to re-run the dispatch validation experiments on an HPC
cluster. They are **templates**: edit the account/partition placeholders and the
solver/license setup for your site before submitting.

- `run_validation_gurobi.slurm` — one scenario with Gurobi.
- `run_validation_cplex.slurm`  — one scenario with CPLEX.
- `run_internal_scaling_baseline.slurm` — **R1**: base under the solver's own scaling knob vs generator-aware.
- `run_hyperparam_sensitivity.slurm`    — **R3**: sweep of `u`, `K`, and the coefficient window.
- `run_stage_ablation.slurm`            — **R5**: local-only / coupling-only / full architecture.

Each job runs all five variants (`base`, `estructurado`=SA-Aug,
`estructurado_matricial`=SA-Mat, `ruiz`=Ruiz, `ruiz_columnas`=Ruiz+Cols) over one
instance class at one MIP gap, writing a `resumen.csv` (and per-instance logs/CSVs)
under `results/<TAG>/`. Submit one job per (class × solver × gap); 12 jobs reproduce
the full study. These are long runs (hours–days; the Full class is the slowest).

Before submitting:

1. Build the solver binary: `cd code && make USE_HEXALY=0` (needs Gurobi/CPLEX).
2. Edit `--account` / `--qos` / `--partition` and the solver/license environment.
3. Set `CLASS`, `MIPGAP`, and `TAG` at the top of the script.
4. `sbatch cluster/run_validation_gurobi.slurm` (from the repository root).

The original study ran on ClusterUY (Singularity container, 16 cores, 12 GB; the Full
class used more memory). No site-specific identifiers, mail addresses, or license paths
are stored here.

## Revision experiments (peer-review round)

These three templates add the controls requested in review. They reuse the same
`scripts/validar_preprocesamiento.py` runner and the same matched-pairs / verification
machinery, so their outputs drop straight into `scripts/analisis_tesis_preproc.py`.

### R1 — solver-internal-scaling baseline (`run_internal_scaling_baseline.slurm`)

Answers "is the gain just generic scaling the solver could have done itself?". One job
per `(class × gap × solver)` runs (a) the generator-aware variants under **default**
internal scaling, and (b) the **unscaled** model under each native scaling option
(Gurobi `ScaleFlag ∈ {0,1,2,3}`; CPLEX `Read::Scale ∈ {-1,0,1}`), each in its own
`results/r1-internal-scaling/<TAG>/<sub>/` folder sharing the same instances. Compare the
`base` solver time across (b) against `estructurado`/`estructurado_matricial` in (a): if a
tuned internal flag matches the generator-aware variant, the distinctive claim deflates;
if not, it is isolated. New flags: `--scaleflag <-1..3>` / `--cplexscale <-1..1>` on
`configurarSolver`.

### R3 — hyperparameter sensitivity (`run_hyperparam_sensitivity.slurm`)

Sweeps the near-identity band `u ∈ {1.5,2,4}`, Ruiz iterations `K ∈ {2,4,8}`, and the
admissible coefficient window `∈ {[1e-6,1e6],[1e-9,1e9],[1e-12,1e12]}` on the Simple class
under Gurobi. Each point is a folder under `results/r3-hyperparam/`, all sharing `base`.
Confirms the runtime conclusions and the Ruiz "irregularity" are not artifacts of the fixed
constants. New flags on `preprocesar`: `--banda-identidad <u>`, `--ventana-coef <εmin> <εmax>`
(`K` is the existing `--ruiz-iters`); reachable from the runner via `--extra-prep "..."`.

### R5 — operational stage ablation (`run_stage_ablation.slurm`)

Runs the full local--block--coupling architecture and its two single-stage ablations
(`estructurado_solo_local`, `estructurado_solo_acoplamiento`, plus matrix-only twins)
against the same `base`, per class, under Gurobi. Comparing the three attributes the Gurobi
effect to local-row normalization vs coupling-row treatment. New flags on `preprocesar`:
`--solo-local`, `--solo-acoplamiento`.

All three are byte-compatible additions: without the new flags the runner reproduces the
original 12-scenario study unchanged.
