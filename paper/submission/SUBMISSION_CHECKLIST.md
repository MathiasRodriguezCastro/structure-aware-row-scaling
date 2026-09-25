# Submission checklist — Mathematical Programming Computation

Everything below is prepared. The three items marked **you** need an account I do not have.

## Upload to the editorial system

| Item | File | Note |
|---|---|---|
| Manuscript PDF | `paper/mpc/main_mpc.pdf` | 25 pages, figures embedded, built from the sources below |
| LaTeX sources | `paper/submission/mpc-submission.zip` | includes `svjour3.cls`, `svglov3.clo`, `spmpsci.bst`, the `.bbl`, sections, tables and vector figures, so it compiles without the class installed |
| Cover letter | `paper/mpc/cover-letter.pdf` | one page |
| Online Resource 1 | `paper/supporting-information.pdf` | 11 pages; also inside the bundle |
| Online Resource 2 | `paper/submission/reproducibility-artifact.zip` | 20 MB; if the portal refuses it, cite the release link instead |
| Artifact link | `https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.0-mpc-submission` | fixed release, three assets, 358 MB in total |

The manuscript's data-availability statement names the repository and that release, so a referee
who reads only the PDF can still find the artifact.

## Metadata the form will ask for

- **Title.** Pre-Export Row Scaling for Generated Mixed-Integer Programs: Mechanism Attribution
  and Residual-Budget Contracts.
- **Abstract.** 241 words, as in the PDF; MPC asks for 150--250.
- **Keywords (6).** Mixed-integer linear programming; Row scaling; Numerical reliability;
  Equilibration; Residual budgets; Computational reproducibility.
- **MSC 2020.** 90C11, 65F35, 90-08, 65G50, checked against the AMS list.
- **Author.** Mathias Rodríguez Castro, sole author, Facultad de Ingeniería, Universidad de la
  República, Montevideo, Uruguay, mathiasr@fing.edu.uy.
- **Declarations.** No funding; no competing interests; AI assistance disclosed in the manuscript;
  not under consideration elsewhere.

## Three things that need your account

1. **ORCID** (**you**). Springer asks for it "if available", so it is optional, but it is free and
   worth having. Register at <https://orcid.org/register>, then put the identifier in the
   submission form. If you also want it in the paper, the line to edit is the `\institute` block
   of `paper/mpc/main_mpc.tex` (via `scripts/research/build_mpc.py`), plus `CITATION.cff` and
   `.zenodo.json`. I did not invent one.

2. **Zenodo DOI** (**you**). `.zenodo.json` is ready and names this release. Two routes:
   - *Manual upload*, which is what I recommend: at <https://zenodo.org/uploads/new>, upload the
     three release assets (`mpc-submission.zip`, `reproducibility-artifact.zip`,
     `fixed-basis-exports.tar.zst`) and `main_mpc.pdf`, paste the metadata from `.zenodo.json`,
     set "Related identifiers" to the release URL with relation *is supplement to*, and publish.
   - *GitHub integration* (<https://zenodo.org/account/settings/github/>): simpler, but it
     archives only the repository source tarball. The 337 MB deposit and the built archives would
     **not** be included, which defeats the purpose here. If you use it, add those files to the
     record afterwards.

   Once the DOI exists, tell me and I will put it in `CITATION.cff`, `.zenodo.json`, the README
   and, if you want it in the paper, the data-availability statement.

3. **Submission itself** (**you**). I have not submitted or uploaded anything to the journal.

## Rebuild and re-verify

```bash
python3 scripts/research/build_mpc.py           # MPC manuscript from paper/main.tex
make -C paper && make -C paper si               # article and supplement
python3 scripts/research/package_submission.py  # the three archives and the checksums
python3 scripts/research/validate_submission.py # extract, verify, rebuild from the bundle alone
```

The deposit archive is rebuilt with

```bash
tar --sort=name --owner=0 --group=0 --numeric-owner -cf - \
    results-revision/research-audit/fixed-basis-final-20260914/fresh \
    results-revision/research-audit/fixed-basis-recovery-20260914-v2 \
    results-revision/research-audit/fixed-basis-recovery-20260914 \
    data/benchmark-v1 | zstd -6 -T0 -o paper/submission/data-deposit/fixed-basis-exports.tar.zst
```

## One thing to decide about the logs

`results-revision/research-audit/operational/cluster-logs/` holds 242 native Gurobi logs, which
are the evidence for the operational reconstruction. Gurobi masks the WLS access ID and secret in
its own output, but each log header prints `LicenseID to value 2849920` and the academic
registration line with a partially masked address. That is an account identifier rather than a
credential, and the recorded hashes of those files are part of the claims audit, so I published
them as they are. If you would rather scrub the identifier, say so: it means rewriting those
files and re-recording their hashes.
