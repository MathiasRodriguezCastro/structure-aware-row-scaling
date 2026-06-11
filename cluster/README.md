# Cluster job templates (reproduction level N2)

Generic SLURM templates to re-run the dispatch validation experiments on an HPC
cluster. They are **templates**: edit the account/partition placeholders and the
solver/license setup for your site before submitting.

- `run_validation_gurobi.slurm` — one scenario with Gurobi.
- `run_validation_cplex.slurm`  — one scenario with CPLEX.

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
