# COAP manuscript

The active manuscript is **Pre-Export Row Scaling in Generated Mixed-Integer Programs:
Mechanism Attribution and Residual-Budget Contracts**, by Mathias Rodríguez Castro,
prepared for Computational Optimization and Applications on 2 October 2026.
The editorial revision is documented in [COAP_NOTES.md](coap/COAP_NOTES.md).
Publication, journal acceptance and external submission are not claimed.

## Build

From the repository root:

```bash
make research-analysis
make paper
```

Or, to compile the already generated tables and figures:

```bash
make -C paper
```

The outputs are `coap/main_coap.pdf`, the prepared article, and
`supporting-information.pdf`, Online Resource 1. `main.tex` is the source the Springer version
is generated from; building it also produces a `main.pdf` in this layout, which is a local
artifact and is not tracked. The current `Makefile`
uses `pdflatex -halt-on-error` and BibTeX for the main article, and pdfLaTeX for the
supplement. The source uses the standard `article` class, not the old Wiley template.
The required TeX packages include geometry, fontenc, lmodern, microtype, amsmath,
amssymb, amsthm, mathtools, graphicx, booktabs, tabularx, array, enumitem, natbib,
hyperref, xcolor, cleveref and lineno. A TeX Live installation with the recommended
and extra LaTeX packages plus Latin Modern fonts provides these dependencies.

## Source and data map

| File or directory | Purpose |
|---|---|
| `main.tex` | Main manuscript, experimental design, results and declarations. |
| `sections/identifiability.tex` | Exact collapse, identity-band bounds and analytic matrix examples. |
| `sections/residual_contract.tex` | Residual-budget compatibility, minimax factors, rounding allowance and exact dyadic export. |
| `sections/related_work.tex` | Positioning relative to prior work. |
| `sections/matrix_replication.tex` | Fresh matrix attribution audit and its limits. |
| `supporting-information.tex` | Supplement and reproducibility details. |
| `research-references.bib` | Bibliography used by the current manuscript. |
| `tables/`, `figs/research/` | Current generated table fragments and publication figures. |
| `research-audit/` | Mathematical/evidence/literature audits and preserved earlier versions. |

The authoritative results are `../results-revision/research-audit/budget-final/`,
`identifiability-final/`, and `operational/`. The first two are newly generated
experiments; the third reconstructs 240 historical dispatch runs from saved records
and native logs. The root [README](../README.md) documents the protocol, checks,
optional reruns, and reasons for retaining intermediate datasets.

`make research-analysis` regenerates the budget table and two figures, the matrix
summary and figure, and the operational summaries. It copies the generated
operational table into `tables/operational-results.tex` for inclusion by the article.
These analyses need no optimizer or commercial license. `make research-check-python`
checks the saved binary evidence and matrix hashes; `make research-check` also builds
and tests the actual C++ LP exporter.

Earlier draft sources and PDFs are preserved in `research-audit/baseline-20260908/`,
together with the Wiley class, style, bibliography and image files that draft needs, so
that it stays buildable without leaving them in this directory. That draft's positive
block-attribution claim and journal-specific presentation have been superseded, and none
of those files is a dependency of the current PDF build. The working notes and latexdiff
output of earlier revision rounds are in `research-audit/`.

The manuscript and supplement require the author's final scientific and submission
review. Their preparation as PDFs does not imply external peer review, acceptance,
or deposition. The manuscript is outside the repository's code/data licenses unless
an explicit manuscript license is subsequently supplied.

The local [submission preparation](submission/README.md) includes the cover letter,
source ZIP and reproducibility archive. Actual PDF page counts and archive checks are recorded in `submission/VALIDATION.json`. Authorship, no external funding and no competing
interests have been confirmed; the AI declaration is included in the article.
