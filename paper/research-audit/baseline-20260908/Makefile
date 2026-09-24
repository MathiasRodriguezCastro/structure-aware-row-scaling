# Build the manuscript PDF (Wiley New Journal Design v5 template, IJNME / AMA style).
# The WileyNJDv5 class REQUIRES XeLaTeX (it loads the bundled OpenType fonts in Fonts/
# via fontspec) and a TeX Live 2022-era toolchain (the template states TL2023 is
# unsupported).
MAIN = main
SI = supporting-information
.PHONY: all si clean
all: $(MAIN).pdf si
$(MAIN).pdf: $(MAIN).tex references.bib WileyNJDv5.cls $(wildcard figs/*.pdf)
	xelatex -interaction=nonstopmode $(MAIN)
	bibtex $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
si: $(SI).pdf
$(SI).pdf: $(SI).tex $(wildcard figs/esc2_*.pdf)
	xelatex -interaction=nonstopmode $(SI)
	xelatex -interaction=nonstopmode $(SI)
clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).pag $(MAIN).pdf $(MAIN).spl \
	      $(SI).aux $(SI).log $(SI).out $(SI).pdf
