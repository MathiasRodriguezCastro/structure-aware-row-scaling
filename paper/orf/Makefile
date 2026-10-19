.PHONY: all clean
all: main_orf.pdf ESM_1.pdf cover-letter.pdf title-page.pdf

main_orf.pdf: main_orf.tex sn-jnl.cls sn-basic.bst research-references.bib $(wildcard sections/*.tex tables/*.tex figs/research/*.pdf)
	pdflatex -halt-on-error -interaction=nonstopmode main_orf
	bibtex main_orf
	pdflatex -halt-on-error -interaction=nonstopmode main_orf
	pdflatex -halt-on-error -interaction=nonstopmode main_orf

ESM_1.pdf: ESM_1.tex $(wildcard sections/*.tex tables/*.tex figs/research/*.pdf)
	pdflatex -halt-on-error -interaction=nonstopmode ESM_1
	pdflatex -halt-on-error -interaction=nonstopmode ESM_1

cover-letter.pdf: cover-letter.tex
	pdflatex -halt-on-error -interaction=nonstopmode cover-letter
	pdflatex -halt-on-error -interaction=nonstopmode cover-letter

title-page.pdf: title-page.tex
	pdflatex -halt-on-error -interaction=nonstopmode title-page
	pdflatex -halt-on-error -interaction=nonstopmode title-page

clean:
	rm -f *.aux *.log *.out *.blg *.bbl *.pdf
