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

Unless otherwise stated, the data files in `data/` and the aggregate result files
`results/*/resumen.csv` are released under the Creative Commons Attribution 4.0
International License (CC BY 4.0) for academic and research use. Please cite the
paper using `CITATION.cff`.

In summary:

- **Code** is licensed separately under MIT (`LICENSE`).
- **Real dispatch instances** used in the paper are included for reproducibility.
- **Synthetic instances** are fully generated and are included as well.
- **Aggregate results** (`results/*/resumen.csv`) stay in the repository tree.
- **Full per-instance logs and dispatch CSVs** are distributed as external archives
  **only because of their size** — to keep the repository light and clonable — not
  because of any access restriction. The same CC BY 4.0 terms apply to them.

The aggregate results were produced by the original ClusterUY runs; the cleaned
`code/` reproduces the same monolithic MIP + preprocessing path. When reusing the
data, please also cite the dispatch-model references listed in the paper.
