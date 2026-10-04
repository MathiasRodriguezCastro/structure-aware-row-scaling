# COAP manuscript

**Pre-Export Row Scaling in Generated Mixed-Integer Programs: Mechanism Attribution and
Residual-Budget Contracts**, by Mathias Rodríguez Castro, prepared for Computational
Optimization and Applications.

## Build and validation

From the repository root:

```bash
make paper
make research-online-resources
make research-claims
python3 scripts/research/package_submission.py
python3 scripts/research/validate_submission.py
```

The submission PDF is `coap/main_coap.pdf`. Its source is generated directly from `main.tex`
by `scripts/research/build_coap.py`. The `main.pdf` build is a local journal-neutral view of
the same article. Online Resource 1 is `supporting-information.pdf`.

PDF compilation needs pdfLaTeX, BibTeX and the TeX packages listed in the root
[README](../README.md). The Springer class and bibliography styles are included in `coap/`.
The independent claims verifier uses stored experiments and imports no optimizer.

## Files

| Path | Contents |
|---|---|
| `main.tex` | Canonical manuscript, results and declarations |
| `coap/` | Current Springer source, class/style files, bibliography, figures and cover letter |
| `supporting-information.tex`, `supporting-information.pdf` | Online Resource 1 |
| `sections/` | Mathematical results and related work |
| `tables/`, `figs/research/` | Tables and figures used by the current manuscript |
| `research-references.bib` | Current bibliography |
| `validation/` | Independent numerical-claim verification |
| `submission/` | [Submission packages and instructions](submission/README.md) |

`submission/VALIDATION.json` records the bundle compilation, checksum checks and clean
extraction of Online Resource 2. The latter includes the exact Online Resource 1 PDF,
so the documented Online Resource audit works from that artifact alone.

Authorship, funding, competing interests and AI assistance are stated in the manuscript.
The manuscript is outside the source-code and data licenses unless an explicit manuscript
license is supplied. This preparation does not claim journal submission or acceptance.
