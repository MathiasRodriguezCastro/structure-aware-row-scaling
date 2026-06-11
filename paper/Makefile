# Build the preprint/review-layout PDF.
MAIN = main
.PHONY: all clean
all: $(MAIN).pdf
$(MAIN).pdf: $(MAIN).tex references.bib $(wildcard figs/*.pdf)
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN)
	bibtex $(MAIN)
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN)
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN)
clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).pdf $(MAIN).spl
