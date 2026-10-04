# Reproducibility inputs

## Fixed-basis exports

The current COAP release carries `fixed-basis-exports.tar.zst`, containing the exported LP
text and bases of the fixed-basis audit: 337 MB compressed and 5.18 GB uncompressed in
11,585 files. The manifest and checksum are in `paper/submission/data-deposit/`.
Online Resource 2 includes the stored summaries and native logs used by its verification commands.

Download the bulk archive from the
[current release](https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.2-coap-submission)
and extract it over the repository before running `make research-fixed-basis-check`.
The Zenodo concept DOI is [10.5281/zenodo.20648949](https://doi.org/10.5281/zenodo.20648949).

## Dispatch collection records

The source dispatch collections retain their original metadata under `results/`.
Their per-instance solver logs and dispatch CSVs are attached to the
[data-collection release](https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.0.1).
The per-scenario `manifest.json` and `checksums.sha256` identify and verify those files.
The current operational reconstruction includes its required native logs in Online Resource 2.

To inspect a collection archive, extract its `logs` or `resultados` directory into the
matching `results/<scenario>/` directory and verify it against that collection's manifest.
Those records retain their observation provenance and are not new optimizer runs.
