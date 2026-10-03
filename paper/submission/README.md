# Submission package

Target venue: **Computational Optimization and Applications** (Springer).
The [official guidelines](https://link.springer.com/journal/10589/submission-guidelines)
were checked on 2 October 2026: abstract 150–250 words, 4–6 keywords, numerical citations,
full DOI links and editable sources. The Springer Nature template is recommended;
the existing svjour3 layout is retained. This package has not been externally submitted.

## What to upload

Upload the following files **separately** in Editorial Manager. Ready-to-upload copies
are generated in `editorial-manager/` by `python3 scripts/research/prepare_editorial_uploads.py`.
The packaging script also runs that step automatically.

| File in `editorial-manager/` | Role |
|---|---|
| `main_coap.pdf` | Manuscript PDF |
| `coap-submission.zip` | Editable LaTeX sources, class/style files, bibliography, tables and figures |
| `cover-letter.pdf` | Cover letter |
| `ESM_1.pdf` | Supplementary material: Online Resource 1 |
| `ESM_2.zip` | Supplementary material: Online Resource 2, code and stored experiment data |

`ESM_1.pdf` is byte-identical to `../supporting-information.pdf`; `ESM_2.zip` is
byte-identical to `reproducibility-artifact.zip`. Existing repository names are retained.
Online Resource 2 is **not inside** `coap-submission.zip`: upload `ESM_2.zip` as a separate
supplementary file. The copy of Online Resource 1 inside the source bundle likewise does not
replace its separate supplementary upload. The manuscript's accompanying source/data archive
therefore remains supplied, and its wording needs no change.

`editorial-manager/UPLOAD_INSTRUCTIONS.md` gives upload roles and captions to paste into the
supplementary-file fields. `editorial-manager/SHA256SUMS` verifies all five upload copies.
The journal-neutral layout in `paper/main.tex` is the source from which the Springer version
is generated, not another article PDF to upload.

## The bulk data behind the fixed-basis audit

The reproducibility archive carries the analyses and the summaries they read, and leaves out the
bulk inputs: the exported LP text and bases of the fixed-basis audit, its two earlier recovery
runs, and the benchmark of the descoped campaign. Those are deposited as one archive,
`data-deposit/fixed-basis-exports.tar.zst` -- 337 MB compressed, 5.18 GB in 11,585 files, with
its checksum and contents in `data-deposit/MANIFEST.json`. Only
`make research-fixed-basis-check`, which rebuilds all 1,530 bases from the LP text, needs the
files themselves; every number in the manuscript is reproducible from the summaries in the
reproducibility archive without them.

The archives and the deposit are build products: they are rebuilt by the packaging script and
attached to the tagged release, not carried in the repository history.

## How it is produced and checked

```bash
python3 scripts/research/build_coap.py          # regenerate the COAP manuscript from paper/main.tex
make -C paper && make -C paper si              # rebuild the original layout and the supplement
python3 scripts/research/package_submission.py # rebuild the two submission archives and the checksums
python3 scripts/research/validate_submission.py# extract each archive, verify it, rebuild the bundle
```

`VALIDATION.json` records the last check: every archive's checksums verified, and the COAP bundle
recompiled from its own contents alone, with no overfull boxes and no undefined references.
`SHA256SUMS` covers the archives and the PDFs. `paper/coap/COAP_NOTES.md` lists every change the
journal format required, the fidelity checks against the original manuscript, the abstract word
counts, the MSC codes and the decisions left for the author.

Neither script uploads or submits anything.
