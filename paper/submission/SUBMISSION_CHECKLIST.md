# Submission checklist — Mathematical Programming Computation

Everything below is prepared and was regenerated from the current build. Two items need an
account I do not have, and they are marked **you**.

Springer's guideline pages could not be retrieved from this machine (the site serves a
JavaScript challenge), so the form fields below are what the manuscript provides, not a
transcription of the journal's current requirements. Check the form as you fill it.

## Upload to the editorial system

| Item | File | Note |
|---|---|---|
| Manuscript PDF | `paper/mpc/main_mpc.pdf` | 33 pages, figures embedded, built from the sources below |
| LaTeX sources | `paper/submission/mpc-submission.zip` | 1.2 MB; carries `svjour3.cls`, `svglov3.clo`, `spmpsci.bst`, the `.bbl`, sections, tables and vector figures, so it compiles without the class installed |
| Cover letter | `paper/mpc/cover-letter.pdf` | one page |
| Online Resource 1 | `paper/supporting-information.pdf` | 14 pages; also inside the bundle |
| Online Resource 2 | `paper/submission/reproducibility-artifact.zip` | 20 MB; if the portal refuses it, cite the release link instead |
| Artifact link | `https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling` | the release tag is named in the manuscript's availability statement |

`python3 scripts/research/validate_submission.py` extracts each archive, verifies its
checksums and rebuilds the manuscript from the bundle alone; the last run rebuilt it to 32
pages with no overfull boxes and no undefined references.

## Metadata the form will ask for

- **Title.** Pre-Export Row Scaling in Generated Mixed-Integer Programs: Mechanism Attribution
  and Residual-Budget Contracts.
- **Abstract.** 245 words, as in the PDF.
- **Keywords (6).** Mixed-integer linear programming; Row scaling; Numerical reliability;
  Equilibration; Residual budgets; Computational reproducibility.
- **MSC 2020.** 90C11, 65F35, 90-08, 65G50, checked against the AMS list.
- **Author.** Mathias Rodríguez Castro, sole author, Facultad de Ingeniería, Universidad de la
  República, Montevideo, Uruguay, mathiasr@fing.edu.uy.
- **Declarations.** No funding; no competing interests; sole author; ethics not applicable; AI
  declaration in the manuscript; not under consideration elsewhere.

## Needs your account

1. **ORCID** (**you**). Free, a few minutes, at <https://orcid.org/register>. Set the identifier's
   visibility to everyone so it can be verified. Give it to me and it goes into the manuscript,
   the supplement, `CITATION.cff` and `.zenodo.json`; I did not invent one.

2. **The editorial system** (**you**). Account, upload, form. Everything it asks about the
   manuscript is above.

## Zenodo: already done

The GitHub integration has been active since June, so every release is archived automatically.
The concept DOI, which always resolves to the latest version, is **10.5281/zenodo.20648949**.
Nothing needs to be done by hand; a refreshed release produces a new version DOI, and that
number is the one to cite for the exact reviewed state.
