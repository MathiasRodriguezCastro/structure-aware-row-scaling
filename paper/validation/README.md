# Independent numerical verification

Run `make research-claims` from the repository root. The verifier imports no optimizer and
reads stored model and solver observations. It writes `claims.json` and
`lattice-export-equivalence.csv` here, recording independently enumerated binary optima,
acceptance checks, matrix-export hashes, native operational logs and paired comparisons.

The source is `scripts/research/verify_manuscript_claims.py`. Package-level compilation,
checksum and extracted-artifact checks are recorded in `paper/submission/VALIDATION.json`.
