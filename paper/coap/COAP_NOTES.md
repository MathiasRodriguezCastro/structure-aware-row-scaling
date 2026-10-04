# COAP manuscript

Target: Computational Optimization and Applications.
Guidelines: https://link.springer.com/journal/10589/submission-guidelines
Scope: https://link.springer.com/journal/10589/aims-and-scope

The Springer svjour3 source is generated directly from paper/main.tex by
scripts/research/build_coap.py. The journal-number banner and placeholder dates are suppressed.
The abstract contains 239 whitespace-separated words. Six keywords and the MSC codes
90C11, 65F35, 90-08 and 65G50 are supplied. The AI declaration is in Statements and Declarations.

Build: make -C paper all
Package: python3 scripts/research/package_submission.py
Verify: python3 scripts/research/validate_submission.py

Online Resource 1 is supporting-information.pdf, uploaded as ESM_1.pdf. Online Resource 2 is
reproducibility-artifact.zip, uploaded as ESM_2.zip. It includes the exact Online Resource 1 PDF.
The two supplements must be uploaded separately in Editorial Manager.

The current release is v1.2-coap-submission. Numerical inputs, experimental records, theorem
statements, results, tables and figures retain their existing provenance. All preparation files
in this directory describe the current COAP manuscript.
