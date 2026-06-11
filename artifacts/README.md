# External artifacts (heavy logs and per-instance results)

To keep the repository light and clonable, the **full solver logs** and **per-instance
dispatch CSVs** of the 12 scenarios are not stored in the git tree. They are packaged as
compressed archives and distributed separately. This is a size decision only; there is no
access restriction on these data.

- `<scenario>_logs.tar.zst` — the per-instance solver logs of a scenario (all variants).
  One archive per scenario (12 in total).
- `<scenario>_resultados.tar.zst` — the per-instance dispatch / postprocess CSVs of a
  Gurobi scenario (6 in total; CPLEX scenarios emit no per-instance CSVs).

`<scenario>` matches the folder names in [`../results/`](../results/), e.g.
`validacion-preproc-simple_logs.tar.zst`,
`validacion-preproc-simple_resultados.tar.zst`.

Total compressed size: ~180 MB.

## Where to download

The archives are attached to the **GitHub Release `v1.0.1`** of this repository:

- Release page:
  <https://github.com/MathiasRodriguezCastro/generator-aware-row-scaling/releases/tag/v1.0.1>
- Direct download pattern:
  `https://github.com/MathiasRodriguezCastro/generator-aware-row-scaling/releases/download/v1.0.1/<archive-name>`

For example:

```bash
BASE=https://github.com/MathiasRodriguezCastro/generator-aware-row-scaling/releases/download/v1.0.1
curl -LO $BASE/validacion-preproc-simple_logs.tar.zst
curl -LO $BASE/validacion-preproc-simple_resultados.tar.zst
```

The repository is also archived on Zenodo (concept DOI
[`10.5281/zenodo.20648950`](https://doi.org/10.5281/zenodo.20648950)). The Zenodo
record archives the source tarball; these heavy archives stay on the GitHub release
unless attached to the Zenodo record manually.

## Integrity

Each `results/<scenario>/manifest.json` records `logs_archive`, `logs_archive_sha256`,
`results_archive`, and `results_archive_sha256`; each `results/<scenario>/checksums.sha256`
lists the same hashes. After downloading, verify:

```bash
sha256sum -c results/<scenario>/checksums.sha256   # run from the scenario folder
```

## Using the artifacts (reproduction level beyond N0)

The paper tables/figures (level **N0**) are rebuilt from the in-tree `resumen.csv` alone
and do **not** need these archives. The archives are needed only to:

1. **Rebuild `resumen.csv` from the raw logs** (verifies the parsing step):
   ```bash
   tar --zstd -xf validacion-preproc-simple_logs.tar.zst -C results/validacion-preproc-simple/
   python scripts/reparsear_resumen.py results/validacion-preproc-simple
   ```
2. **Inspect raw per-instance solver logs or dispatch solutions** (extract the relevant
   `*_logs.tar.zst` / `*_resultados.tar.zst` into the matching `results/<scenario>/`).

## Regenerating the archives from a full run

If you re-run the experiments yourself (level N2), the archives are produced from each
output folder with:

```bash
tar -C <output-folder> --zstd -cf <scenario>_logs.tar.zst logs
tar -C <output-folder> --zstd -cf <scenario>_resultados.tar.zst resultados   # Gurobi only
```
