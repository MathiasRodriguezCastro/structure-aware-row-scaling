# Independent numerical verification

Run `make research-claims` from the repository root. The verifier imports no optimizer and
reads stored model and solver observations. It writes `claims.json` and
`lattice-export-equivalence.csv` here, recording independently enumerated binary optima,
acceptance checks, matrix-export hashes, native operational logs and paired comparisons.

The source is `scripts/research/verify_manuscript_claims.py`. Package-level compilation,
checksum and extracted-artifact checks are recorded in `paper/submission/oms/VALIDATION.json`.
The parent directory's `VALIDATION.json` describes the earlier COAP archive.

The v1.3.9 matched accuracy/remedy replay checks 144 terminal candidates, twelve
exact feasible witnesses and 1,244,160 physical row/point combinations. It retains
one additional interrupted attempt under a documented host-reboot amendment.
`oms-v1.3.9-editorial-check.json` proves unchanged abstract, two contributions and
previous activation/IF tables; the new comparison appears in Table S16. Clean
standalone-archive replay with solver execution/imports blocked is documented in
`exploration/oms-matched-accuracy-20261016/PACKAGE_VALIDATION.json`.
