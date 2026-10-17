# Current OMS manuscript and supplementary information; COAP files are historical.
MAIN = main
SI = supporting-information
OMS = oms/main_oms
PYTHON ?= python3
.PHONY: all si oms coap clean
all: $(MAIN).pdf si oms
$(MAIN).pdf: $(MAIN).tex research-references.bib $(wildcard sections/*.tex tables/*.tex figs/research/*.pdf)
	pdflatex -halt-on-error -interaction=nonstopmode $(MAIN)
	bibtex $(MAIN)
	pdflatex -halt-on-error -interaction=nonstopmode $(MAIN)
	pdflatex -halt-on-error -interaction=nonstopmode $(MAIN)
si: $(SI).pdf
$(SI).pdf: $(SI).tex $(wildcard sections/*.tex tables/*.tex)
	pdflatex -halt-on-error -interaction=nonstopmode $(SI)
	pdflatex -halt-on-error -interaction=nonstopmode $(SI)

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).pdf $(SI).aux $(SI).log $(SI).out $(SI).pdf
	rm -f $(OMS).aux $(OMS).bbl $(OMS).blg $(OMS).log $(OMS).out $(OMS).pdf

oms: $(OMS).pdf oms/cover-letter.pdf
$(OMS).tex: $(MAIN).tex ../scripts/research/build_oms.py $(wildcard sections/*.tex tables/*.tex) research-references.bib
	cd .. && $(PYTHON) scripts/research/build_oms.py
$(OMS).pdf: $(OMS).tex oms/interact.cls oms/tfq.bst $(wildcard oms/sections/*.tex oms/tables/*.tex oms/figs/research/*.pdf)
	cd oms && pdflatex -halt-on-error -interaction=nonstopmode main_oms && bibtex main_oms && pdflatex -halt-on-error -interaction=nonstopmode main_oms && pdflatex -halt-on-error -interaction=nonstopmode main_oms
oms/cover-letter.pdf: oms/cover-letter.tex
	cd oms && pdflatex -halt-on-error -interaction=nonstopmode cover-letter && pdflatex -halt-on-error -interaction=nonstopmode cover-letter

# The canonical sources now target OMS; do not mix them with the old COAP front matter.
coap:
	@echo "Rebuild COAP from archived v1.2-coap-submission; current sources target OMS."
	@false
