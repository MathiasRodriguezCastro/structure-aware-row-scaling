# COAP editorial revision — 2 October 2026

Target: Computational Optimization and Applications.
Official guidelines: https://link.springer.com/journal/10589/submission-guidelines
Scope: https://link.springer.com/journal/10589/aims-and-scope

The Springer svjour3 layout is retained. The journal recommends its newer template;
editable sources and the compiled PDF are supplied. The manuscript-number banner and placeholder received/accepted dates are suppressed.
The abstract contains 239 whitespace-separated words.

Changes: mechanism and accuracy contract precede attribution methodology and computational
validation; the abstract follows the same hierarchy; Related Work explicitly distinguishes
mechanism attribution and original-unit guarantees from Elble–Sahinidis scaler comparisons;
the sixth keyword is Finite-precision optimization. A new COAP cover letter is provided.
The AI declaration remains in Statements and Declarations. MSC codes are unchanged.

No results, theorem statements, tables, figures, experiments or limitations were changed.
The COAP revision is frozen in v1.1.1-coap-submission. The existing v1.0-mpc-submission
artifact DOI/tag identifies the earlier archived version. The concept DOI identifies the series.
Previous MPC sources and PDFs are preserved in paper/mpc; make mpc can regenerate its layout
from the current canonical source. The active build and package use paper/coap.

Build: make -C paper all
Package: python3 scripts/research/package_submission.py
Verify: python3 scripts/research/validate_submission.py
See paper/submission/VALIDATION.json for actual document lengths and bundle checks.

Repository citation and Zenodo metadata describe the COAP revision and use the release tag
v1.1.1-coap-submission. Earlier MPC records and tags retain their historical identifiers.

Maintenance correction before submission: Online Resource 1 now says "All three solvers use
one thread". Online Resource 2 includes the exact supplement PDF and the two cited historical
summary directories. README links to excluded historical material point to the full repository
or its historical tags. Validation extracts Online Resource 2, compares its PDF to Online
Resource 1, verifies relative README links and runs make research-online-resources successfully.
