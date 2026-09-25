# Mathematical Programming Computation submission version

This directory holds the MPC (Springer `svjour3`) version of the manuscript. The canonical
manuscript in `paper/` is untouched. Nothing scientific was changed: the body of `main_mpc.tex`
is the body of `paper/main.tex`, and the sections, tables, figures and bibliography are
byte-identical copies (verified, see *Fidelity check*).

## How it is built

```bash
python3 scripts/research/build_mpc.py      # regenerates main_mpc.tex from paper/main.tex
cd paper/mpc && pdflatex main_mpc && bibtex main_mpc && pdflatex main_mpc && pdflatex main_mpc
```

`build_mpc.py` copies the body verbatim and applies only the format-driven changes listed
below, so the MPC version can be refreshed whenever the canonical manuscript changes. The
abstract lives in `abstract.tex` because it is the one piece of prose that differs.

The class files (`svjour3.cls`, `svglov3.clo`, `spmpsci.bst`, `spbasic.bst`) come from the
official Springer macro package linked from the journal's submission guidelines
(`468198_LaTeX_DL_468198_240419.zip`); they are not in TeX Live. `readme.txt` and `history.txt`
are Springer's own files, kept for provenance.

## Changes required by the format

1. **Document class.** `\documentclass[smallextended,envcountsect,envcountsame]{svjour3}`,
   replacing `article` with one-inch margins. The two `envcount` options are not cosmetic: the
   class numbers theorem-like environments continuously by default, and without them every
   cross-reference in the paper would renumber. With them the numbering is the original one --
   a single counter, numbered within the section (Proposition 4.1, 4.2, 4.3, 5.1, 5.3,
   Corollary 5.2).
2. **Packages removed.** `geometry` (the class sets the page), `lineno` (line numbers are for
   internal review), `lmodern` (the class chooses the font), `amsthm` (the class defines the
   theorem-like environments itself and clashes with it).
3. **Packages added.** `fix-cm` and `\smartqed`, as the Springer template requires; `xurl`,
   because a long reference URL does not break in the narrower measure and overflowed the text
   block; `\emergencystretch=1.5em`, which absorbs the few lines that no longer break as well.
   `microtype`, `amsmath`, `amssymb`, `mathtools`, `graphicx`, `booktabs`, `tabularx`, `array`,
   `enumitem`, `natbib`, `hyperref` and `cleveref` are kept from the original preamble.
4. **Cross-reference naming.** The class defines its theorem-like environments with
   `\spnewtheorem`, and with `envcountsame` they share the `theorem` counter, which is what
   `cleveref` keys on. Left alone, `\cref{prop:...}` printed *Theorem 4.1* where the original
   prints *Proposition 4.1*. Fixed with `\crefname{theorem}{Proposition}{Propositions}`, which
   is exact here because every theorem-like environment in the paper is a proposition except one
   corollary, and that corollary is never cross-referenced. **If a theorem is ever added, or the
   corollary is ever cited, this has to be revisited.**
5. **Front matter.** `\title`, `\author`, `\institute` with `\email`, `\date{Received: date /
   Accepted: date}` and `\journalname`, as the template prescribes. `\titlerunning` and
   `\authorrunning` were added so the running heads fit. Title, author, affiliation and email are
   unchanged. No ORCID was invented.
6. **Abstract, keywords, MSC** now sit inside the `abstract` environment as the class expects.
   The keywords are the original six, reformatted with `\and`. See below for the abstract.
7. **Declarations moved after the references**, as requested. Their text is unchanged:
   *Funding and competing interests*, *Authorship and computational resources*, *Use of AI
   assistance*. *Data and software availability* and *Supplementary information* keep their
   position before the references, and the references to Online Resource 1 and Online Resource 2
   are unchanged. The supplement is not merged into the article.
8. **Bibliography style** `spmpsci` (Springer, mathematical and physical sciences, numbered),
   replacing `plainnat`. The `.bib` file is unchanged: no entry, author, title, year, DOI or URL
   was touched, and all 19 entries are still cited.
9. **Three wide tables scaled.** The Springer text block is about a quarter narrower than the
   original layout, and Tables 3, 4 and 5 overflowed it. Each is wrapped in
   `\resizebox{\textwidth}{!}{...}`; the table sources are untouched, so every number, column and
   alignment is the one in `paper/tables/`.

## Fidelity check

- The body of `main_mpc.tex` and `paper/main.tex` differ only by the two blank lines left where
  the declarations were removed, the bibliography style, and the three `\resizebox` wrappers.
  Everything else is byte-identical, verified by diff after normalising exactly those items.
- `sections/*.tex`, `tables/*.tex`, `research-references.bib` and the three figure PDFs are
  byte-identical copies (SHA-256 compared).
- Proposition and corollary numbers match the original PDF exactly: Proposition 4.1 (5
  occurrences), 4.2 (2), 4.3 (3), 5.1 (5), 5.3 (3), Corollary 5.2 (1), and no stray "Theorem".
- Every reported value, policy name, solver version and instance or run count was compared
  between the two rendered PDFs: 0.698, 0.682, 0.777, 0.778, 1.077, 1.078, 30--32\%, 4,320, 1,530,
  1,080, 4,752, 10.2, 4.27, 4.97, Base, Flat-GM, Flat-L2, Role-Hybrid, SA-Mat, SA-Pre, GM-tight,
  Budget-only, Budget-GM, Budget-dyadic, Budget-round, GCD-floor, HiGHS 1.15.1, Gurobi 13.0.2,
  CPLEX 22.1.2, SG-Ter-Mer, instance077, caso46e, "96 models", "240 assigned runs". The only
  count differences are artefacts of the extraction: the original PDF carries review line numbers,
  and the narrower measure hyphenates a few policy names across lines. The sources agree exactly.
- Conclusions, section titles and figure and table numbering are unchanged.

## Abstract

MPC asks for roughly 150--250 words. The manuscript abstract was **272 words**; the MPC abstract
is **241**, deliberately short of the limit because an editorial system that splits hyphenated
terms would count more. All nine required messages are kept: the fixed-basis audit on 306 models; six to eight
orders of magnitude; the coupling-kernel rather than block-metadata explanation; the optimal
factor $(1+\rho^2)^{-1/2}$; residual-budget contracts; the SG-Ter-Mer solver-work result; the
seed and solver sensitivity; the stress test with verified optima; and the distinction between a
numerical improvement and operational safety.

What was cut, and nothing else: two sentences were merged, "This paper asks" became "We ask",
"A gain of that size does not identify the information behind it" became "Such a gain does not
identify its cause", "holding one LP basis fixed across the representations of each model" became
"holding each model's LP basis fixed across its representations", "which row factors a budget and
coefficient limits admit" became "the row factors compatible with a budget and coefficient
limits", the redundant second mention of the unbudgeted comparator was dropped (the clause still
says "adding the budget to that same rule"), "on all three solvers tested" became "on all three
solvers", and the hinge sentence "Such a gain does not identify its cause" was removed because
the sentence that follows it makes the same point.

## MSC 2020 codes proposed

```
\subclass{90C11 \and 65F35 \and 90-08 \and 65G50}
```

Checked against the AMS list (`mathscinet.ams.org/msnhtml/msc2020.pdf`), where each title below
appears verbatim:

- **90C11** Mixed integer programming.
- **65F35** Numerical computation of matrix norms, conditioning, scaling.
- **90-08** Computational methods for problems pertaining to operations research and
  mathematical programming.
- **65G50** Roundoff error.

The first draft used **65K05** (numerical mathematical programming methods) as the fourth code.
The review replaced it with 65G50: the paper proposes no solution method, while the rounding
term, the binary64 export conditions and the residual budgets are squarely about roundoff.
**90C06** (large-scale problems) was considered and left out, since the paper is not about
problem size. Editors sometimes adjust these, but they are now verified rather than guessed.

## Remaining warnings

- 0 overfull boxes, 0 undefined references, 0 undefined citations, 0 LaTeX warnings.
- 2 underfull `\vbox` warnings from page breaking around floats. Cosmetic; they do not affect
  content and are usual in a float-heavy article.
- 25 pages in the Springer layout, against 21 in the original.

## Submission package

`paper/submission/mpc-submission.zip` carries everything an editor needs: `main_mpc.tex` and
`abstract.tex`, the sections, tables and vector figures, the bibliography and `main_mpc.bbl`,
the four Springer class and style files, the compiled manuscript, the cover letter, these notes,
and the supplement as Online Resource~1. Online Resource~2 is
`paper/submission/reproducibility-artifact.zip`. Rebuild both with
`python3 scripts/research/package_submission.py`, then check them with
`python3 scripts/research/validate_submission.py`, which extracts each archive, verifies its
checksums and recompiles the manuscript from the bundle alone. The last run: checksums verified
for all three archives, and the bundle rebuilt to 25 pages with no overfull boxes and no
undefined references, using only the class files it ships.

## Decisions that need your approval

0. **The MSC codes are now verified rather than proposed** (see above), and the fourth changed
   from 65K05 to 65G50. Tell me if you prefer the original four.
1. **The two `envcount` class options.** You asked for `\documentclass[smallextended]{svjour3}`
   and for the numbering to be preserved; those two requirements conflict, and I chose to keep
   the numbering. If you prefer the bare option line, the propositions renumber continuously and
   every cross-reference changes with them.
2. **The `\crefname` override** described in change 4, which is exact for the current text but
   would have to be revisited if a theorem is added or the corollary is cited.
3. **The MSC codes**, which are a proposal.
4. **The scaled tables**, which are the least invasive way to fit the narrower measure. The
   alternative is to typeset them at `\footnotesize` in a full-width `table*`.
5. **The abstract**, at 241 words, for you to compare with the 272-word original.
