# Data license and terms

This file covers the **data** in the repository; the source code is licensed
separately under the MIT `LICENSE`.

## What is included and why

- **Dispatch instances** (`data/entradas/`): the real input instances of the three
  classes (Simple, Full, SG-Ter-Mer) used in the paper, included for reproducibility.
- **Synthetic instances** (`data/synthetic/`): fully generated block-structured grids
  used by the mechanism check; they contain no real operational data.
- **Aggregate results** (`results/*/resumen.csv`): per-(instance, variant) summary
  metrics, kept in the repository tree.
- **Heavy artifacts** (full per-instance logs and dispatch CSVs): distributed as
  external archives (see `artifacts/README.md`). They are external **only because of
  their size**, to keep the repository light and clonable — not because of any access
  restriction.

## Terms

Unless a more specific notice is added, the data files in `data/` and `results/` are
released for academic reproducibility of the accompanying paper. If you reuse them,
please cite the paper (see `CITATION.cff`) and the dispatch-model references listed in
the paper. The aggregate results were produced by the original ClusterUY runs; the
cleaned `code/` reproduces the same monolithic MIP + preprocessing path.
