#!/usr/bin/env python3
"""Build the ORF editorial adaptation from the preserved OMS scientific text."""
import re
import shutil
from orf_config import ROOT, PAPER, ORF, TITLE, VERSION


def fragment(name):
    text = (ORF/'editorial'/name).read_text()
    return re.sub(r'\\input\{editorial/([^}]+)\}',
                  lambda m: fragment(m[1]+'.tex'), text)


def relabel(text):
    # Retain internal scientific labels and data paths; change published SI names.
    text = re.sub(r'Supplementary\s+Material\s*~?\s*([12])', r'Online Resource~\1', text)
    text = re.sub(r'\bMaterial\s*~?\s*([12])', r'Online Resource~\1', text)
    text = text.replace('new OMS experiments', 'later experiments')
    text = text.replace('Additional OMS dispatch validation','Additional dispatch validation')
    text = text.replace('local OMS\ncampaigns','additional local\ncampaigns')
    return text


EDITORIAL_CUTS = (
    ('Here the contracts provide a conditional precision interpretation and an auditable\n'
     'admissibility rule, rather than a performance improvement or an operational calibration.',
     'Here the contracts make factor admissibility and original-unit precision auditable.'),
    ('These results establish a useful, configuration-dependent\n'
     'representation choice and verification workflow; admissibility does not certify MILP\n'
     'optimality. ', ''),
    (' Lower work or absence of\n'
     'a detected flag does not certify bounds or optimality.', ''),
    (' No MILP optimality certificate is implied.', ''),
    ('Ratios below\n'
     'one indicate a faster process on the shared host; they do not establish a\n'
     'hardware-independent threshold for applying scaling.',
     'Ratios below one indicate a faster process on the shared host.'),
    ('These controls strengthen the\n'
     'within-family effort comparison without establishing a generally superior rule.', ''),
    (' These additional checks do not certify every native MILP result.', ''),
    (' Budget compliance alone therefore does\nnot imply feasibility of all domains.', ''),
    (' Satisfied primal budgets do not certify solver bounds.', ''),
    ('; absence of a flag does not certify optimality.', '.'),
)


def refine_editorial(text, strict=False):
    """Remove listed duplicate prose only; equations and numerical inputs stay intact."""
    for original, replacement in EDITORIAL_CUTS:
        if strict:
            assert text.count(original)==1, 'Editorial anchor changed: '+original
        text=text.replace(original,replacement)
    return text


def main():
    original = (PAPER/'main.tex').read_text()
    source = original.split(r'\section{Introduction}', 1)[1]
    source = r'\section{Introduction}' + source
    opening_end = source.index('Evaluation presents a second problem.')
    source = r'\section{Introduction}'+'\n'+(ORF/'editorial/opening.tex').read_text()+'\n'+source[opening_end:]
    source = source.replace('Evaluation presents a second problem.',
        (ORF/'editorial/workflow.tex').read_text()+'\nEvaluation presents a second problem.',1)
    start = source.index('Evaluation presents a second problem.')
    end = source.index('This paper makes two main contributions', start)
    source = source[:start]+(ORF/'editorial/evaluation-framing.tex').read_text()+'\n'+source[end:]
    items = re.search(r'(This paper makes two main contributions.*?)(\\begin\{enumerate\}.*?\n)(.*?)(\\end\{enumerate\})', source, re.S)
    assert items is not None
    contributions = re.split(r'(?=\\item )', items[3])
    contributions = [s for s in contributions if s.startswith(r'\item ')]
    assert len(contributions)==2
    source = source[:items.start(3)] + (ORF/'editorial/contributions.tex').read_text() + source[items.end(3):]
    start = source.index(r'\paragraph{Computational validation.}')
    end = source.index(r'\input{sections/related_work}', start)
    source = source[:start]+(ORF/'editorial/validation-overview.tex').read_text()+'\n'+source[end:]
    source = source.replace(r'\section{Discussion and conclusions}',
        fragment('prospective-main.tex')+'\n'+fragment('verified-main.tex')+'\n'+fragment('confirmation-main.tex')+'\n'+r'\section{Discussion and conclusions}',1)
    start = source.index(r'\subsection{Implications for scaling software}')
    end = source.index(r'\subsection{Scope and limitations}', start)
    source = source[:start]+(ORF/'editorial/discussion.tex').read_text()+'\n'+source[end:]
    source = source.replace(r'\subsection{Scope and limitations}',
        (ORF/'editorial/practical.tex').read_text()+'\n'+r'\subsection{Scope and limitations}',1)
    start = source.index(r'\subsection{Conclusions}')
    end = source.index(r'\section*{Data and software availability}',start)
    source = source[:start]+fragment('scope-extension.tex')+'\n'+fragment('conclusions.tex')+'\n'+source[end:]
    start = source.index(r'\section*{Data and software availability}')
    end = source.index(r'\section*{Acknowledgements}',start)
    source = source[:start]+(ORF/'editorial/availability.tex').read_text()+'\n'+source[end:]
    # Springer asks for methodological documentation of use beyond copy editing.
    disclosure = ('\\paragraph{Research-tool documentation}\n'
        'OpenAI ChatGPT and Codex and Anthropic Claude assisted software development,\n'
        'verification code, mathematical checks and manuscript preparation. The AI\n'
        'declaration under Statements and Declarations documents their use and the\n'
        "author's verification responsibilities.\n\n")
    source = source.replace(r'\label{sec:experiments}'+'\n',
                            r'\label{sec:experiments}'+'\n'+disclosure,1)
    # The class selects sn-basic.bst itself; Numbered selects bracketed citations.
    source = source.replace(r'\bibliographystyle{plainnat}'+'\n','')
    source = source.replace('The accompanying source and data archive\nis Supplementary Material 2.',
                            'Online Resource~2 contains the source and data archive.')
    source = relabel(source)
    start = source.index(r'\section*{Acknowledgements}')
    end = source.index(r'\section*{Statements and Declarations}',start)
    source = source[:start]+r'\section*{Acknowledgements}'+'\n'+fragment('acknowledgements.tex')+'\n'+source[end:]
    source = refine_editorial(source,strict=True)
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
    preamble += '\\usepackage{tikz}\n'
    front = r"""
\hypersetup{pdftitle={TITLE},pdfauthor={Mathias Rodr\'iguez Castro}}
\graphicspath{{figs/research/}}
\emergencystretch=1.5em
\raggedbottom
\setcounter{secnumdepth}{3}
% These tables have no threeparttable notes. Its automatic tabular measurement
% conflicts with boxed external inputs; retain the underlying publisher float.
\let\table\tableorg
\let\endtable\endtableorg
\begin{document}
\title[Accuracy-aware row scaling]{TITLE}
\author*[1]{\fnm{Mathias} \sur{Rodr\'iguez Castro}}
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
    supplement = supplement[:reproduction]+fragment('prospective-supplement.tex')+'\n'+fragment('export-errors.tex')+'\n'+fragment('verified-supplement.tex')+'\n'+fragment('confirmation-supplement.tex')+'\n'+fragment('reproduction.tex')+'\n'+r'\end{document}'+'\n'
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
                section = relabel(path.read_text())
                if path.name=='residual_contract.tex':
                    anchor = r'\paragraph{Verification after solving}'
                    assert section.count(anchor)==1
                    section = section.replace(anchor,fragment('export-selector-main.tex')+'\n'+anchor)
                dest.write_text(section)
            else:
                shutil.copyfile(path,dest)
    (ORF/'research-references.bib').write_text((PAPER/'research-references.bib').read_text()+
        '\n'+(ORF/'editorial/additional-references.bib').read_text())
    print('Generated ORF manuscript and Online Resource 1:',VERSION)
    print('Abstract source tokens:',len(abstract.split()))


if __name__=='__main__':
    main()
