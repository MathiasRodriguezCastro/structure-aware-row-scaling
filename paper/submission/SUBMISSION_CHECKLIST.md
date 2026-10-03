# Submission checklist — Computational Optimization and Applications

Prepared on 2 October 2026 for the fixed release v1.1.1-coap-submission.
Journal submission is not claimed.
Guidelines: https://link.springer.com/journal/10589/submission-guidelines

| Item | File |
|---|---|
| Manuscript PDF | `paper/coap/main_coap.pdf` |
| Editable sources and class files | `paper/submission/coap-submission.zip` |
| Cover letter | `paper/coap/cover-letter.pdf` |
| Online Resource 1 — separate supplementary upload | `paper/submission/editorial-manager/ESM_1.pdf` |
| Online Resource 2 — separate supplementary upload | `paper/submission/editorial-manager/ESM_2.zip` |

Generate the upload copies with `python3 scripts/research/prepare_editorial_uploads.py`.
Upload both ESM files separately, as supplementary material. Online Resource 2 is not inside
the manuscript source ZIP. The names inside the repository are unchanged. Captions for both
resources are in `editorial-manager/UPLOAD_INSTRUCTIONS.md`.

Title: Pre-Export Row Scaling in Generated Mixed-Integer Programs: Mechanism Attribution and Residual-Budget Contracts.
Keywords (6): Mixed-integer linear programming; Row scaling; Numerical reliability;
Equilibration; Residual budgets; Finite-precision optimization.
MSC: 90C11, 65F35, 90-08, 65G50.
Author: Mathias Rodríguez Castro, Facultad de Ingeniería, Universidad de la República,
Montevideo, Uruguay; mathiasr@fing.edu.uy; ORCID 0009-0002-7235-7677.
Declarations: no external funding; no competing interests; sole author; ethics not applicable;
AI assistance disclosed in Statements and Declarations.

Use `coap/abstract.tex` for the submission abstract. Consult `VALIDATION.json` for verified
page counts and checksums; `validate_submission.py` checks archives and recompiles the bundle.
The editor's portal may request additional metadata. Author review and upload remain pending.

The existing computational artifact is pinned to v1.0-mpc-submission,
DOI https://doi.org/10.5281/zenodo.23104497; the concept DOI is
https://doi.org/10.5281/zenodo.20648949. The COAP editorial revision is frozen in v1.1.1-coap-submission; its archive is a separate
version under the same concept DOI. The earlier version DOI continues to identify the MPC release.

Previous COAP version DOI: https://doi.org/10.5281/zenodo.23112768. The release archive is public at
https://zenodo.org/records/23112768.

The corrected supplementary files are supplied in v1.1.1-coap-submission.
