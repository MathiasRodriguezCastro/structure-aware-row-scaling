# Aggregate experimental results

This directory holds the **aggregate outputs** of the dispatch experiments reported in
the paper. Each scenario folder is kept light and contains only:

- `resumen.csv` — one row per (instance, variant) with all the metrics used by the
  analysis scripts (times, deterministic work/dettime, solver conditioning, nodes,
  gaps, objective deviations, original-scale feasibility, …).
- `manifest.json` — scenario metadata (class, solver, version, MIP gap, time limit,
  threads, variants, instance count, checksums, external-artifact names, provenance).
- `checksums.sha256` — SHA-256 of `resumen.csv` and of the external artifacts.

> **Provenance.** These aggregate results come from the original ClusterUY runs (full
> binary, monolithic path; the LSTM/Dantzig–Wolfe code was present but unused). The
> cleaned `code/` in this repository reproduces the same monolithic MIP + preprocessing
> path. The heavy per-instance solver logs and dispatch CSVs are distributed as external
> artifacts (see [`../artifacts/README.md`](../artifacts/README.md)) to keep the
> repository light and clonable — this is a size decision, not an access restriction.

The analysis at reproduction level **N0** rebuilds every paper table and figure from the
`resumen.csv` files alone, with no solver:

```bash
make analysis-n0            # from the repository root
```

## The 12 scenarios

Variants in every scenario: `base`, `estructurado` (SA-Aug), `estructurado_matricial`
(SA-Mat), `ruiz` (Ruiz), `ruiz_columnas` (Ruiz+Cols). Time limit 3600 s, 16 threads.

| Class | Solver | MIP gap | Instances | Folder | External artifacts |
|-------|--------|---------|-----------|--------|--------------------|
| Simple | Gurobi | 1e-2 | 204 | `validacion-preproc-simple` | logs + resultados |
| Simple | Gurobi | 1e-3 | 204 | `validacion-preproc-simple-gap0001` | logs + resultados |
| Simple | CPLEX | 1e-2 | 204 | `validacion-preproc-simple-cplex-ute` | logs |
| Simple | CPLEX | 1e-3 | 204 | `validacion-preproc-simple-cplex-ute-gap0001` | logs |
| Full | Gurobi | 1e-2 | 34 | `validacion-preproc-completo` | logs + resultados |
| Full | Gurobi | 1e-3 | 34 | `validacion-preproc-completo-gap0001` | logs + resultados |
| Full | CPLEX | 1e-2 | 34 | `validacion-preproc-completo-cplex-ute` | logs |
| Full | CPLEX | 1e-3 | 34 | `validacion-preproc-completo-cplex-ute-gap0001` | logs |
| SG-Ter-Mer | Gurobi | 1e-2 | 68 | `validacion-preproc-sg-ter-mer` | logs + resultados |
| SG-Ter-Mer | Gurobi | 1e-3 | 68 | `validacion-preproc-sg-ter-mer-gap0001` | logs + resultados |
| SG-Ter-Mer | CPLEX | 1e-2 | 68 | `validacion-preproc-sg-ter-mer-cplex-ute` | logs |
| SG-Ter-Mer | CPLEX | 1e-3 | 68 | `validacion-preproc-sg-ter-mer-cplex-ute-gap0001` | logs |

CPLEX scenarios have no `resultados` archive: on this platform CPLEX does not emit
per-instance solution CSVs; its objective and the rigorous original-scale equivalence
check are read from the solver log. The `-ute` suffix in the CPLEX folder names is the
original ClusterUY partition tag and carries no other meaning.

Deeper reproduction (rebuild `resumen.csv` from the raw logs, or re-run the solver) is
described in the top-level `README.md` (levels N1–N2) and in `artifacts/README.md`.
