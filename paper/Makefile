# Current COAP manuscript and supplementary information.
MAIN = main
SI = supporting-information
COAP = coap/main_coap
PYTHON ?= python3
.PHONY: all si coap clean
all: $(MAIN).pdf si coap
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
	rm -f $(COAP).aux $(COAP).bbl $(COAP).blg $(COAP).log $(COAP).out $(COAP).pdf

# The COAP source is generated directly from main.tex.
coap: $(COAP).pdf coap/cover-letter.pdf
$(COAP).tex: $(MAIN).tex coap/abstract.tex ../scripts/research/build_coap.py $(wildcard sections/*.tex tables/*.tex) research-references.bib
	cd .. && $(PYTHON) scripts/research/build_coap.py
$(COAP).pdf: $(COAP).tex $(wildcard coap/sections/*.tex coap/tables/*.tex coap/figs/*.pdf)
	cd coap && pdflatex -halt-on-error -interaction=nonstopmode main_coap && bibtex main_coap && pdflatex -halt-on-error -interaction=nonstopmode main_coap && pdflatex -halt-on-error -interaction=nonstopmode main_coap
coap/cover-letter.pdf: coap/cover-letter.tex
	cd coap && pdflatex -halt-on-error -interaction=nonstopmode cover-letter && pdflatex -halt-on-error -interaction=nonstopmode cover-letter
