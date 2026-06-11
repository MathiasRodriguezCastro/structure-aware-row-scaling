# Paper sources

`main.tex` is the manuscript (elsarticle review layout, IJNME free-format). It is
self-contained: tables are embedded and figures are read from `figs/`.

```
cd paper
make            # pdflatex -> bibtex -> pdflatex x2  =>  main.pdf
```

The compiled PDF is a reproducible preprint/review layout and **not** the final Wiley
typeset version. Bibliography: `references.bib` (`\bibliographystyle{elsarticle-harv}`).
Figures: `figs/` holds the dispatch scenario plots (`esc{1..4}_*`) and the synthetic
benchmark plots (`fig{1..4}_*`), regenerated from the data/results in this repository.
