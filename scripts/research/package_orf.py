#!/usr/bin/env python3
"""Prepare an ORF delivery with the unchanged, audited scientific archive."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import unicodedata
import zipfile
from orf_config import ROOT, PAPER, ORF, OUT, VERSION, DATE, TITLE, PARENT, PARENT_DIR, FOLLOWUP, FOLLOWUP_ARCHIVE, sha

FILES = ('main_orf.pdf','orf-editable-sources.zip','cover-letter.pdf','title-page.pdf','ESM_1.pdf','ESM_2.zip')
EXTRAS = ('REPRODUCE.md','UPLOAD_INSTRUCTIONS.md','ONLINE_RESOURCE_CAPTIONS.txt',
          'FORM_FIELDS.json','REPRODUCTION-VALIDATION.json','SHA256SUMS')
SCIENCE = 'scientific-evidence-oms-v1.3.17.zip'


def write_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def archive(path, entries):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        hashes=[]
        for name, value in sorted(entries.items()):
            if isinstance(value,Path):
                z.write(value,name);digest=sha(value)
            else:
                value=value.encode() if isinstance(value,str) else value
                z.writestr(name,value);digest=hashlib.sha256(value).hexdigest()
            hashes.append(f'{digest}  {name}\n')
        z.writestr('CONTENTS.sha256',''.join(hashes))


def plain(text):
    text=text.replace(r'\,',' ').replace(r'\textsuperscript{3}','³').replace('$10^{-9}$','10⁻⁹').replace(r'\%','%')
    text=re.sub(r"\\'\{?([A-Za-z])\}?",lambda m:unicodedata.normalize('NFC',m[1]+'\u0301'),text)
    for name in ('path','url','texttt','emph'):
        text=re.sub(r'\\'+name+r'\{([^{}]*)\}',r'\1',text)
    text=re.sub(r'\\doi\{([^{}]*)\}',r'https://doi.org/\1',text)
    text=text.replace(r'\_','_').replace('~',' ')
    assert '\\' not in text,text
    return ' '.join(text.split())


def build_delivery(validation=None):
    uploads=OUT/'uploads'
    write_json(uploads/'REPRODUCTION-VALIDATION.json',{
        'snapshot_version':VERSION,'status':'passed' if validation else 'not_yet_validated',
        'validation':validation})
    names=FILES+EXTRAS
    (uploads/'SHA256SUMS').write_text(''.join(f'{sha(uploads/n)}  {n}\n' for n in names if n!='SHA256SUMS'))
    with zipfile.ZipFile(OUT/'orf-delivery.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in names:z.write(uploads/name,name)
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(uploads/n)}  uploads/{n}\n' for n in FILES)+
        f'{sha(OUT/"orf-delivery.zip")}  orf-delivery.zip\n')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parent_archive=PARENT_DIR/'reproducibility-artifact.zip'
    parent_validation=json.loads((PARENT_DIR/'VALIDATION.json').read_text())
    assert parent_validation['snapshot_version']==PARENT
    assert sha(parent_archive)==parent_validation['archives']['reproducibility-artifact.zip']['sha256']
    with zipfile.ZipFile(parent_archive) as z:
        for name in ('paper/main.tex','paper/supporting-information.tex'):
            assert z.read(name)==(ROOT/name).read_bytes(),'Scientific source drift: '+name
    entries={}
    for name in ('main_orf.tex','main_orf.bbl','main_orf.pdf','ESM_1.tex','ESM_1.pdf',
                 'cover-letter.tex','cover-letter.pdf','sn-jnl.cls','sn-basic.bst',
                 'title-page.tex','title-page.pdf',
                 'research-references.bib','TEMPLATE_PROVENANCE.md','Makefile'):
        entries[name]=ORF/name
    for folder in ('sections','tables','figs/research'):
        for p in (ORF/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.tex','.pdf'):entries[p.relative_to(ORF).as_posix()]=p
    entries['README.md']='Current ORF editable sources. Run make in this directory with pdfLaTeX and BibTeX.\n'
    source_zip=OUT/'orf-editable-sources.zip';archive(source_zip,entries)
    followup_validation=json.loads((FOLLOWUP/'VALIDATION.json').read_text())
    assert followup_validation['status']=='passed' and followup_validation['MIP_calls']==360
    logging_validation=json.loads((FOLLOWUP/'logging-confirmation/VALIDATION.json').read_text())
    assert logging_validation['status']=='passed' and logging_validation['MIP_calls']==360
    assert logging_validation['complete_native_logs']==360
    cluster_validation=json.loads((FOLLOWUP/'CLUSTER_VALIDATION.json').read_text())
    assert cluster_validation['status']=='passed'
    assert cluster_validation['analysis_sha256']==sha(FOLLOWUP/'CLUSTER_ANALYSIS.json')
    followup_entries={p.relative_to(ROOT).as_posix():p for p in FOLLOWUP.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.zip')}
    followup_zip=OUT/FOLLOWUP_ARCHIVE;archive(followup_zip,followup_entries)
    # Canonical editorial inputs and build tools, distinct from the scientific archive.
    revision={}
    roots=['README.md','CITATION.cff','.zenodo.json','LICENSE','DATA_LICENSE.md','Makefile',
           'paper/Makefile','paper/README.md','paper/main.tex','paper/supporting-information.tex',
           'paper/research-references.bib','paper/orf/Makefile','paper/orf/README.md',
           'paper/orf/TEMPLATE_PROVENANCE.md','paper/orf/REVISION_NOTES.md','paper/orf/cover-letter.tex','paper/orf/title-page.tex','paper/orf/sn-jnl.cls','paper/orf/sn-basic.bst',
           'paper/submission/orf/README.md','paper/submission/orf/SUBMISSION_CHECKLIST.md',
           'scripts/research/orf_config.py','scripts/research/build_orf.py',
           'scripts/research/package_orf.py','scripts/research/validate_orf.py','scripts/research/freeze_orf.py']
    for name in roots:revision[name]=ROOT/name
    for folder in ('paper/orf/editorial','paper/sections','paper/tables','paper/figs/research'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.tex','.pdf','.bib'):revision[p.relative_to(ROOT).as_posix()]=p
    revision_zip=OUT/'orf-revision-sources.zip';archive(revision_zip,revision)
    snapshot={'version':VERSION,'date':DATE,'target':'Operations Research Forum','title':TITLE,
        'published':False,'submitted':False,'version_doi':None,'new_optimization_experiments':720,
        'prospective_primary_MIP_calls':360,'logging_confirmation_MIP_calls':360,
        'new_exact_LP_attempts':96,'prospective_archive_sha256':sha(followup_zip),
        'prospective_validation_sha256':sha(FOLLOWUP/'VALIDATION.json'),
        'cluster_analysis_sha256':sha(FOLLOWUP/'CLUSTER_ANALYSIS.json'),
        'cluster_analysis_is_post_hoc':True,'cluster_resamples':100000,'scenario_clusters':24,
        'scientific_parent':PARENT,'scientific_archive_sha256':sha(parent_archive),
        'scientific_parent_validation_sha256':sha(PARENT_DIR/'VALIDATION.json'),
        'current_sources_sha256':sha(source_zip),'canonical_revision_sha256':sha(revision_zip),
        'scientific_source_unchanged':True,
        'editorial_changes':['accuracy workflow first','practical framing and implications',
            'Springer template and numbered bibliography','Online Resource names and reproduction instructions',
            'new cover letter and ORF declarations/portal preparation',
            'prospective 24-scenario validation, 360 primary MIP calls, 360 logging confirmations and rational references',
            'finite-export error bound, concise discussion, workflow figure and uncluttered author line',
            'main-text prospective outcome table, candidate-cost qualification and post hoc scenario-cluster uncertainty'],
        'journal_instructions':'https://link.springer.com/journal/43069/submission-guidelines'}
    write_json(OUT/'SNAPSHOT.json',snapshot)
    captions=('Online Resource 1: Supplementary proofs, full experimental protocols and controls, '
        'exact arithmetic checks, numerical limitations and reproduction instructions.\n\n'
        'Online Resource 2: Current ORF sources, prospective scenario evidence and the unchanged audited scientific code/data '
        'archive, including generators, scaling software, model exports, native logs, saved '
        'solutions, rational witnesses and independent replay programs. Inheritance and '
        'file checksums identify the exact versions.\n')
    guide=f'''# {TITLE}

Journal: Operations Research Forum
Author: Mathias Rodríguez Castro
Affiliation: Facultad de Ingeniería, Universidad de la República, Montevideo, Uruguay
Correspondence: mathiasr@fing.edu.uy
ORCID: https://orcid.org/0009-0002-7235-7677
Local snapshot: {VERSION}; {DATE}. No new Zenodo DOI has been assigned.

ESM_1.pdf is Online Resource 1. ESM_2.zip is the complete Online Resource 2.
The latter contains the exact {PARENT} scientific-evidence ZIP and its validation
record, current editable ORF sources, canonical editorial sources and SNAPSHOT.json.
Historical OMS filenames identify provenance. The current article, letter and
resource captions are addressed to ORF. A separately identified prospective study
adds 24 new within-family scenarios, 360 primary MIP calls, a registered 360-call
logging confirmation and 96 exact LP attempts. The first campaign is retained
with its suppressed native traces; the confirmation supplies complete logs.

## Reproduce the evidence

Extract ESM_2.zip and check its CONTENTS.sha256. Then extract {SCIENCE} into an
empty directory and enter that extracted scientific repository:

```sh
sha256sum --quiet -c CONTENTS.sha256
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r environment/research-requirements.txt
make research-oms-check
make research-check-python
make research-check
make research-analysis
```

Install the system prerequisites listed in environment/apt-packages.txt; the
native export check needs GNU Make and a C++17 compiler. These commands verify
saved results without rerunning research MILPs or requiring a commercial solver
license. Mathematical tests include small SciPy reference LPs. The controls cover
90 new saved calls and 36 reused Budget-L2 points, exact witnesses, original-unit
residuals, paired work and complete-process time. Analysis regenerates 42 tables
and three figures. The scientific archive's paper build preserves its historical
OMS presentation; compile the ORF source bundle for the current documents.

## Replay the prospective study

Extract {FOLLOWUP_ARCHIVE} over the extracted scientific repository, preserving
its exploration/ path. Its CONTENTS.sha256 lists the additional files. From that
repository root run:

```sh
python3 exploration/orf-confirmatory-20261018/check.py
python3 exploration/orf-confirmatory-20261018/check.py --logging-confirmation
python3 exploration/orf-confirmatory-20261018/check_export_bound.py
python3 exploration/orf-confirmatory-20261018/check_cluster_analysis.py
```

These commands check both sets of 360 saved MIP outcomes, complete confirmation
logs, endpoint/point replication, factor interventions, rational
reference certificates and the elementary finite-export bound without commercial
solver calls. The fixed protocol retains known parent data, new scenario
perturbations and three horizon sizes. This is prospective within-family evidence;
it is not a new independent application. The 96 rational LP acquisition attempts
are separately costed and do not certify every returned floating-point candidate.

## Build the current documents

Extract orf-editable-sources.zip separately, verify CONTENTS.sha256 and run `make`.
It supplies pdfLaTeX sources, bibliography, publisher class/style, figures, current
main PDF, Online Resource 1 and letter. orf-revision-sources.zip supplies the
repository-relative canonical editorial inputs and build scripts as well.

To reconstruct the complete package from those canonical revision sources,
create paper/submission/oms/releases/{PARENT}/ beneath the extracted revision
root. Copy {SCIENCE} there as reproducibility-artifact.zip and copy
SCIENTIFIC_PARENT_VALIDATION.json there as VALIDATION.json. Then run
`make paper` and `python3 scripts/research/package_orf.py`. All these inputs
are supplied here; the parent ZIP does not need a separate public download.

Rebuilding all 1,530 historical bases additionally requires the separate baseline
bulk archive at DOI 10.5281/zenodo.23145294. That DOI identifies the historical
baseline, not the later experiments or this submission. The four saved-result
commands above do not need that bulk archive. Fresh timed solver runs require
the documented solver versions and licenses and have hardware-dependent timing.

Code is MIT; data/results are CC BY 4.0. Publisher class/style files retain their
own notices. Manuscript text and PDFs are outside the code/data licenses.
'''
    esm=OUT/'ESM_2.zip'
    archive(esm,{'README.md':guide,'SNAPSHOT.json':OUT/'SNAPSHOT.json',
        FOLLOWUP_ARCHIVE:followup_zip,
        SCIENCE:parent_archive,'SCIENTIFIC_PARENT_VALIDATION.json':PARENT_DIR/'VALIDATION.json',
        'orf-editable-sources.zip':source_zip,'orf-revision-sources.zip':revision_zip,
        'ONLINE_RESOURCE_CAPTIONS.txt':captions,'CITATION.cff':ROOT/'CITATION.cff',
        'zenodo-metadata.json':ROOT/'.zenodo.json','LICENSE':ROOT/'LICENSE','DATA_LICENSE.md':ROOT/'DATA_LICENSE.md'})
    uploads=OUT/'uploads';uploads.mkdir(exist_ok=True)
    for name,origin in {'main_orf.pdf':ORF/'main_orf.pdf','cover-letter.pdf':ORF/'cover-letter.pdf',
                        'title-page.pdf':ORF/'title-page.pdf',
                        'ESM_1.pdf':ORF/'ESM_1.pdf','ESM_2.zip':esm,'orf-editable-sources.zip':source_zip}.items():
        shutil.copyfile(origin,uploads/name)
    (uploads/'REPRODUCE.md').write_text(guide)
    (uploads/'ONLINE_RESOURCE_CAPTIONS.txt').write_text(captions)
    (uploads/'UPLOAD_INSTRUCTIONS.md').write_text('''# ORF separate upload preparation

Extract orf-delivery.zip before assigning individual files in the portal.
main_orf.pdf: manuscript with author details (single-blind review).
orf-editable-sources.zip: editable LaTeX source files.
cover-letter.pdf: editor-only cover letter.
title-page.pdf: author information and title-page acknowledgements; use the portal's
title-page role if requested. Author details also remain in the main manuscript.
ESM_1.pdf: Online Resource 1; ESM_2.zip: Online Resource 2, both for review.
ONLINE_RESOURCE_CAPTIONS.txt gives the supplementary captions.
FORM_FIELDS.json supplies the current title, abstract, keywords and declarations.

The official journal instructions were consulted on 18 October 2026:
https://link.springer.com/journal/43069/submission-guidelines
Confirm the exact portal categories and limits when uploading. Enter author
contributions and competing interests in the interface too. The DOI/deposit
remains deferred by the author; no remote submission or publication was performed.
REPRODUCTION-VALIDATION.json must say passed. SHA256SUMS covers all delivery files.
''')
    abstract=plain((ORF/'editorial/abstract.tex').read_text())
    assert 150<=len(abstract.split())<=250
    scientific_source=(PAPER/'main.tex').read_text()
    declarations={}
    for name,body in re.findall(r'\\paragraph\{([^}]+)\}\s*(.*?)(?=\\paragraph\{|\\section\*?\{|\Z)',scientific_source,re.S):
        if name in ('Funding','Competing interests','Author contributions',
                    'Ethics approval, consent and human or animal participants','AI declaration'):
            declarations[name]=plain(body)
    assert len(declarations)==5
    fields={'version':VERSION,'journal':'Operations Research Forum','proposed_article_type':'Original Research Article',
        'title':TITLE,'abstract':abstract,'abstract_words':len(abstract.split()),
        'keywords':['Mixed-integer programming','Numerical scaling','Feasibility tolerances',
                    'Accuracy contracts','Computational optimization','Reproducibility'],
        'author':{'name':'Mathias Rodríguez Castro','affiliation':'Facultad de Ingeniería, Universidad de la República, Montevideo, Uruguay',
                  'email':'mathiasr@fing.edu.uy','orcid':'0009-0002-7235-7677','corresponding_author':True},
        'MSC_2020':['90C11','65F35','90-08','65G50'],'declarations':declarations,
        'data_availability':plain((ORF/'editorial/availability.tex').read_text().split('}',1)[1]),
        'funding_received':False,'CAP_supported_work':False,'new_version_DOI':None,
        'DOI_deferred_by_author':True,'portal_categories_confirmed':False,'submission_performed':False}
    write_json(uploads/'FORM_FIELDS.json',fields)
    build_delivery()
    print('Prepared full ORF delivery:',VERSION,'abstract words:',len(abstract.split()))


if __name__=='__main__':main()
