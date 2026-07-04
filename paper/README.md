# Paper sources

`main.tex` is the manuscript for the *International Journal for Numerical Methods in
Engineering* (Wiley), prepared with the official **Wiley New Journal Design v5** class:
`\documentclass[AMA,Times1COL]{WileyNJDv5}` (AMA reference style, single-column review
layout with line numbers).

## Building

The WileyNJDv5 class **requires XeLaTeX** (it loads the bundled OpenType fonts in `Fonts/`
through fontspec) and a TeX Live 2022-era toolchain (the template states TeX Live 2023 is
unsupported).

```
cd paper
make            # xelatex -> bibtex -> xelatex x2  =>  main.pdf
```

## Contents
- Reference style: AMA superscript numeric via `wileyNJD-AMA.bst` (selected by the class
  `AMA` option); bibliography database in `references.bib`.
- Figures in `figs/`: dispatch scenario plots (`esc{1..4}_*`) and the synthetic benchmark
  plots, regenerated from the data/results in this repository.

## Class support files (from the Wiley NJD v5 template)
`WileyNJDv5.cls`, `wileyNJD-AMA.bst`, `lettersp.sty`, `rhlogo.jpg` / `empty.pdf` /
`empty.eps`, and the `Fonts/` directory. All other dependencies are standard TeX Live
packages.

> **Note:** `Fonts/` (the bundled OpenType fonts, several of them commercial) is **not
> committed** (see `.gitignore`). Download the official Wiley NJD v5 template and copy its
> `Fonts/` directory next to `main.tex` to reproduce the exact typography. Without it,
> XeLaTeX still compiles but substitutes default fonts.
