# Submission package

Target venue: **Mathematical Programming Computation** (Springer). Its scope is computational
mathematical programming, and it reviews the software and data alongside the manuscript, which
is why the artifact below is part of the submission rather than an afterthought. The journal's
author instructions ask for an abstract of 150--250 words, 4--6 keywords, MSC codes, author and
contact information, declarations and editable sources; all are provided. Nothing here has been
submitted or accepted anywhere.

## What to upload

| File | Role |
|---|---|
| `mpc-submission.zip` | the manuscript in Springer's `svjour3` format, with its class files, sections, tables, vector figures, bibliography, compiled PDF, cover letter, and the supplement as Online Resource 1 |
| `../supporting-information.pdf` | Online Resource 1, also inside the bundle |
| `reproducibility-artifact.zip` | Online Resource 2: code, experiment data, manifests, checksums, tests and reproduction instructions |
| `../mpc/cover-letter.pdf` | cover letter, also inside the bundle |

`manuscript-sources.zip` holds the sources of the original, journal-neutral layout in `paper/`;
it is not part of the MPC upload and is kept so the two layouts stay comparable.

## How it is produced and checked

```bash
python3 scripts/research/build_mpc.py          # regenerate the MPC manuscript from paper/main.tex
make -C paper && make -C paper si              # rebuild the original layout and the supplement
python3 scripts/research/package_submission.py # rebuild the three archives and the checksums
python3 scripts/research/validate_submission.py# extract each archive, verify it, rebuild the bundle
```

`VALIDATION.json` records the last check: every archive's checksums verified, and the MPC bundle
recompiled from its own contents alone, with no overfull boxes and no undefined references.
`SHA256SUMS` covers the archives and the PDFs. `paper/mpc/MPC_NOTES.md` lists every change the
journal format required, the fidelity checks against the original manuscript, the abstract word
counts, the MSC codes and the decisions left for the author.

Neither script uploads or submits anything.
