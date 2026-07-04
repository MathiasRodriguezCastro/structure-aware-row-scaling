# Build the manuscript PDF (Wiley New Journal Design v5 template, IJNME / AMA style).
# The WileyNJDv5 class REQUIRES XeLaTeX (it loads the bundled OpenType fonts in Fonts/
# via fontspec) and a TeX Live 2022-era toolchain (the template states TL2023 is
# unsupported).
MAIN = main
.PHONY: all clean
all: $(MAIN).pdf
$(MAIN).pdf: $(MAIN).tex references.bib WileyNJDv5.cls $(wildcard figs/*.pdf)
	xelatex -interaction=nonstopmode $(MAIN)
	bibtex $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).pag $(MAIN).pdf $(MAIN).spl
