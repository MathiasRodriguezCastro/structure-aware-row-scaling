#!/usr/bin/env python3
"""Build the ORF editorial adaptation from the preserved OMS scientific text."""
import re
import shutil
from orf_config import ROOT, PAPER, ORF, TITLE, VERSION


def relabel(text):
    # Retain internal scientific labels and data paths; change published SI names.
    text = re.sub(r'Supplementary\s+Material\s*~?\s*([12])', r'Online Resource~\1', text)
    text = re.sub(r'\bMaterial\s*~?\s*([12])', r'Online Resource~\1', text)
    text = text.replace('new OMS experiments', 'later experiments')
    text = text.replace('Additional OMS dispatch validation','Additional dispatch validation')
    text = text.replace('local OMS\ncampaigns','additional local\ncampaigns')
    return text


def main():
    original = (PAPER/'main.tex').read_text()
    source = original.split(r'\section{Introduction}', 1)[1]
    source = r'\section{Introduction}' + source
    opening_end = source.index('Evaluation presents a second problem.')
    source = r'\section{Introduction}'+'\n'+(ORF/'editorial/opening.tex').read_text()+'\n'+source[opening_end:]
    items = re.search(r'(This paper makes two main contributions.*?)(\\begin\{enumerate\}.*?\n)(.*?)(\\end\{enumerate\})', source, re.S)
    assert items is not None
    contributions = re.split(r'(?=\\item )', items[3])
    contributions = [s for s in contributions if s.startswith(r'\item ')]
    assert len(contributions)==2
    first = contributions[1].replace('Accuracy-aware scaling and verification software',
                                    'Accuracy-aware model generation and verification')
    second = contributions[0].replace('Numerical impact and mechanism attribution',
                                     'Computational evaluation and mechanism attribution')
    source = source[:items.start(3)] + first + second + source[items.end(3):]
    source = source.replace(r'\subsection{Scope and limitations}',
        (ORF/'editorial/practical.tex').read_text()+'\n'+r'\subsection{Scope and limitations}',1)
    start = source.index(r'\section*{Data and software availability}')
    end = source.index(r'\section*{Acknowledgements}',start)
    source = source[:start]+(ORF/'editorial/availability.tex').read_text()+'\n'+source[end:]
    # Springer asks for methodological documentation of use beyond copy editing.
    disclosure = ('\\paragraph{Research-tool documentation}\n'
        'Assistive use of OpenAI ChatGPT and Codex and Anthropic Claude covered software\n'
        'development, verification code, drafting, literature organization and checks of\n'
        'mathematical derivations. The author independently verified the arguments,\n'
        'protocols, results and interpretations and retains responsibility for them.\n'
        'The declaration at the end of the article records the same scope of use.\n\n')
    source = source.replace(r'\label{sec:experiments}'+'\n',
                            r'\label{sec:experiments}'+'\n'+disclosure,1)
    # The class selects sn-basic.bst itself; Numbered selects bracketed citations.
    source = source.replace(r'\bibliographystyle{plainnat}'+'\n','')
    source = source.replace('The accompanying source and data archive\nis Supplementary Material 2.',
                            'Online Resource~2 contains the source and data archive.')
    source = relabel(source)
    # Fit only tables that otherwise exceed the publisher's text width.
    def fit_table(match):
        if r'\begin{table}' in (PAPER/(match[1]+'.tex')).read_text():
            return match[0]
        return r'\adjustbox{max width=\linewidth}{'+match[0]+'}'
    source = re.sub(r'\\input\{(tables/[^}]+)\}',fit_table,source)
    abstract = (ORF/'editorial/abstract.tex').read_text().strip()
    preamble = original.split(r'\hypersetup',1)[0]
    preamble = preamble.replace(r'\documentclass[11pt]{article}',r'\documentclass[pdflatex,sn-basic,Numbered]{sn-jnl}')
    preamble = preamble.replace(r'\usepackage[margin=1in]{geometry}'+'\n','')
    preamble = preamble.replace(r'\usepackage{lmodern,microtype,amsmath,amssymb,amsthm,mathtools}',
                                r'\usepackage{microtype,amsmath,amssymb,amsthm,mathtools,adjustbox}')
    preamble = preamble.replace(r'\usepackage[numbers,sort&compress]{natbib}'+'\n','')
    preamble = preamble.replace(r'\usepackage[colorlinks=true,allcolors=blue!45!black]{hyperref}'+'\n','')
    preamble = preamble.replace(r'\usepackage{lineno}'+'\n','')
    front = r"""
\hypersetup{pdftitle={TITLE},pdfauthor={Mathias Rodr\'iguez Castro}}
\graphicspath{{figs/research/}}
\emergencystretch=1.5em
\raggedbottom
\setcounter{secnumdepth}{3}
% The distributed class refers to an ORCID logo absent from its ZIP. A text
% hyperlink carries the same author identifier without an external image.
\renewcommand{\orcid}[1]{\href{#1}{\textsuperscript{\normalfont ORCID}}}
% These tables have no threeparttable notes. Its automatic tabular measurement
% conflicts with boxed external inputs; retain the underlying publisher float.
\let\table\tableorg
\let\endtable\endtableorg
\begin{document}
\title[Accuracy-aware row scaling]{TITLE}
\author*[1]{\fnm{Mathias} \sur{Rodr\'iguez Castro}\,\orcid{https://orcid.org/0009-0002-7235-7677}}
\email{mathiasr@fing.edu.uy}
\affil*[1]{\orgname{Facultad de Ingenier\'ia, Universidad de la Rep\'ublica},
\orgaddress{\city{Montevideo}, \country{Uruguay}}}
\abstract{ABSTRACT}
\keywords{Mixed-integer programming, Numerical scaling, Feasibility tolerances,
Accuracy contracts, Computational optimization, Reproducibility}
\pacs[MSC Classification (2020)]{90C11, 65F35, 90-08, 65G50}
\maketitle
""".replace('TITLE',TITLE).replace('ABSTRACT',abstract)
    (ORF/'main_orf.tex').write_text(preamble+front+'\n'+source)
    supplement = (PAPER/'supporting-information.tex').read_text()
    old_title = re.search(r'\\title\{Supplementary Material 1.*?\n\\author',supplement,re.S)
    assert old_title is not None
    supplement = supplement[:old_title.start()] + '\\title{Online Resource 1\\\\\\large Supplement to ``'+TITLE+"''}\n\\author"+supplement[old_title.end():]
    supplement = supplement.replace('Prepared for Optimization Methods and Software','Prepared for Operations Research Forum')
    supplement = supplement.replace('v1.3.17-oms-submission', VERSION)
    reproduction = supplement.index(r'\section{Reproduction and artifact layout}')
    supplement = supplement[:reproduction]+(ORF/'editorial/reproduction.tex').read_text()+'\n'+r'\end{document}'+'\n'
    supplement = relabel(supplement)
    # The original SI reproduction recipe refers to the unchanged scientific archive.
    marker = 'This supplement specifies the computational evidence and its limitations.'
    supplement = supplement.replace(marker,
        'This Operations Research Forum adaptation reuses the scientific evidence of\n'
        '\\path{v1.3.17-oms-submission}. Online Resource~2 contains that exact archived\n'
        'code/data ZIP and the current sources. Unpack its scientific-evidence ZIP\n'
        'before using the repository-relative commands and paths below.\n\n'+marker,1)
    (ORF/'ESM_1.tex').write_text(supplement)
    # Shared experimental inputs are copied byte-for-byte, without relabelling data.
    for folder, suffix in [('tables','.tex'),('sections','.tex'),('figs/research','.pdf')]:
        for path in (PAPER/folder).glob('*'+suffix):
            dest = ORF/folder/path.name
            dest.parent.mkdir(parents=True,exist_ok=True)
            if folder=='sections':
                dest.write_text(relabel(path.read_text()))
            else:
                shutil.copyfile(path,dest)
    shutil.copyfile(PAPER/'research-references.bib',ORF/'research-references.bib')
    print('Generated ORF manuscript and Online Resource 1:',VERSION)
    print('Abstract source tokens:',len(abstract.split()))


if __name__=='__main__':
    main()
