# The main latex-file
TEXFILE = main

# Fix reference file and compile source
default: full

full:
	pdflatex $(TEXFILE) && \
	bibtex $(TEXFILE) && \
	pdflatex $(TEXFILE) && \
	pdflatex $(TEXFILE) && \
	cp $(TEXFILE).pdf report.pdf


# Removes TeX-output files
clean:
	rm -f *.aux $(TEXFILE).bbl $(TEXFILE).blg *.log *.out $(TEXFILE).toc $(TEXFILE).lot $(TEXFILE).lof $(TEXFILE).glg $(TEXFILE).glo $(TEXFILE).gls $(TEXFILE).ist $(TEXFILE).acn $(TEXFILE).acr $(TEXFILE).alg $(TEXFILE).xdy $(TEXFILE).loa
