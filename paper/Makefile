# Portable research revision; historical Wiley sources are preserved in research-audit/.
MAIN = main
SI = supporting-information
MPC = mpc/main_mpc
PYTHON ?= python3
.PHONY: all si mpc clean
all: $(MAIN).pdf si mpc
$(MAIN).pdf: $(MAIN).tex research-references.bib $(wildcard sections/*.tex tables/*.tex figs/research/*.pdf)
	pdflatex -halt-on-error -interaction=nonstopmode $(MAIN)
	bibtex $(MAIN)
	pdflatex -halt-on-error -interaction=nonstopmode $(MAIN)
	pdflatex -halt-on-error -interaction=nonstopmode $(MAIN)
si: $(SI).pdf
$(SI).pdf: $(SI).tex $(wildcard sections/*.tex tables/*.tex)
	pdflatex -halt-on-error -interaction=nonstopmode $(SI)
	pdflatex -halt-on-error -interaction=nonstopmode $(SI)

# The submission version. Its source is derived from $(MAIN).tex, so editing the manuscript
# regenerates it; see mpc/MPC_NOTES.md.
mpc: $(MPC).pdf
$(MPC).tex: $(MAIN).tex mpc/abstract.tex ../scripts/research/build_mpc.py
	cd .. && $(PYTHON) scripts/research/build_mpc.py
$(MPC).pdf: $(MPC).tex mpc/research-references.bib \
            $(wildcard mpc/sections/*.tex mpc/tables/*.tex mpc/figs/*.pdf)
	cd mpc && pdflatex -halt-on-error -interaction=nonstopmode main_mpc \
	    && bibtex main_mpc \
	    && pdflatex -halt-on-error -interaction=nonstopmode main_mpc \
	    && pdflatex -halt-on-error -interaction=nonstopmode main_mpc

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).pdf $(SI).aux $(SI).log $(SI).out $(SI).pdf
	rm -f $(MPC).aux $(MPC).bbl $(MPC).blg $(MPC).log $(MPC).out $(MPC).pdf
