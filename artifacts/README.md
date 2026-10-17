# Reproducibility inputs

## Fixed-basis exports

The archived experimental baseline `v1.2-coap-submission` carries `fixed-basis-exports.tar.zst`, containing the exported LP
text and bases of the fixed-basis audit: 337 MB compressed and 5.18 GB uncompressed in
11,585 files. The manifest and checksum are in `paper/submission/data-deposit/`.
The current OMS Supplementary Material 2 includes the stored summaries and native logs used by its verification commands.
It also includes every compressed LP, named reference basis, row-factor record and saved
incumbent of the additional OMS dispatch comparison; `make research-oms-check` needs no
bulk baseline download or optimization call.

The local frozen OMS version is `v1.3.10-oms-submission`. Its complete new-data inventory is
`paper/submission/oms/OMS_DATA_MANIFEST.json`; the baseline metadata are retained in
`artifacts/baseline-metadata/`. The old DOI does not identify the new OMS experiments.

Download the bulk archive from the
[baseline release](https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.2-coap-submission)
and extract it at the repository root before running `make research-fixed-basis-check`
or a fresh `make research-fixed-basis-precision`. The version DOI is
[10.5281/zenodo.23145294](https://doi.org/10.5281/zenodo.23145294).
The four saved-result audit/analysis commands documented in the root README are
self-contained in OMS Supplementary Material 2 and need no bulk download.
The Zenodo concept DOI is [10.5281/zenodo.20648949](https://doi.org/10.5281/zenodo.20648949).

## Dispatch collection records

The source dispatch collections retain their original metadata under `results/`.
Their per-instance solver logs and dispatch CSVs are attached to the
[data-collection release](https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.0.1).
The per-scenario `manifest.json` and `checksums.sha256` identify and verify those files.
The current operational reconstruction includes its required native logs in Supplementary Material 2.

To inspect a collection archive, extract its `logs` or `resultados` directory into the
matching `results/<scenario>/` directory and verify it against that collection's manifest.
Those records retain their observation provenance and are not new optimizer runs.
